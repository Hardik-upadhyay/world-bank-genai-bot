"""
Banking FAQ Data Ingestion Script
----------------------------------
Generates synthetic banking FAQ data, splits into chunks,
embeds using the MAAS OpenAI-compatible embedding model, and stores in ChromaDB.

Run as standalone:
    cd backend
    python -m app.data.ingest
"""

import os
import sys
import json
import logging
import hashlib
import httpx
import chromadb
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# backend/app/data/ingest.py -> parents[2] = backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
# Load .env from backend/ directory
load_dotenv(BACKEND_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# MAAS embedding model (OpenAI-compatible endpoint)
MAAS_BASE_URL = os.getenv("MAAS_BASE_URL", "https://genailab.tcs.in")
MAAS_API_KEY = os.getenv("MAAS_API_KEY", "")
MAAS_EMBED_MODEL = "azure/genailab-maas-text-embedding-3-large"
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(BACKEND_DIR / "chroma_db"))
COLLECTION_NAME = "banking_faq"

# Initialize MAAS embedding model (SSL verification disabled as required)
_http_client = httpx.Client(verify=False)
embedding_model = OpenAIEmbeddings(
    base_url=MAAS_BASE_URL,
    model=MAAS_EMBED_MODEL,
    api_key=MAAS_API_KEY,
    http_client=_http_client,
)

logger.info("Embedding model: %s (MAAS)", MAAS_EMBED_MODEL)
logger.info("ChromaDB path: %s", CHROMA_DB_PATH)

# ─────────────────────────────────────────────────────────────────────────────
# Synthetic Banking FAQ Dataset
# ─────────────────────────────────────────────────────────────────────────────

BANKING_FAQ_DATA = [
    # ─── Accounts ────────────────────────────────────────────────────────────
    {
        "topic": "savings_account",
        "source": "Account Policy v3.2",
        "content": """Savings Account - Overview and Features
A savings account is the most fundamental banking product offered to retail customers.
It allows customers to deposit money safely and earn interest on their balance.

Key Features:
- Minimum opening balance: ₹1,000 for regular savings; ₹0 for zero-balance accounts
- Interest rate: 3.5% per annum calculated on daily closing balance, credited quarter
- Monthly average balance (MAB): ₹5,000 for urban branches; ₹2,000 for rural
- Free ATM withdrawals: 5 per month at own ATMs; 3 per month at other bank ATMs
- Penalty for falling below MAB: ₹200 + GST per month
- Joint account facility available (Either or Survivor / Anyone or Survivor modes)
- Nomination facility mandatory from Jan 2026

Eligibility:
- Resident Individuals (single or joint)
- Minors above 10 years (guardian-operated below 10)
- Hindu Undivided Families (HUF)
- Associations, Clubs, Societies (with proof of registration)"""
    },
    {
        "topic": "savings_account",
        "source": "Interest Rate Circular 2025-Q4",
        "content": """Savings Account Interest Rates - Effective Q4 2025

Standard Savings Account:
- Balance up to ₹1 lakh: 3.5% p.a.
- Balance ₹1 lakh to ₹10 lakh: 4.0% p.a.
- Balance above ₹10 lakh: 4.25% p.a.

Premium Savings (Advantage Plus):
- All balance tiers: 5.0% p.a. (requires ₹25,000 MAB)

Senior Citizen Savings:
- Additional 0.5% above standard rates on all tiers
- No MAB requirement

Interest is calculated on daily balance and credited quarterly (March, June, September, December).
Interest earned is subject to TDS if annual interest exceeds ₹10,000 (₹50,000 for senior citizens)."""
    },
    {
        "topic": "current_account",
        "source": "Account Policy v3.2",
        "content": """Current Account - Business Banking

A current account is designed for businesses, traders, companies, and professionals
who require frequent transactions without any restrictions.

Key Features:
- No interest paid on current account balance
- Unlimited transactions (deposits, withdrawals, NEFT, RTGS, cheques)
- Overdraft facility available (subject to credit appraisal)
- Minimum balance: ₹10,000 for standard; ₹50,000 for premium business
- Monthly statement by email/post
- Multi-city cheque facility included
- Cash deposit limit: ₹2,00,000 per day free; beyond that ₹2 per ₹1,000

Eligible Entities:
- Proprietorship firms
- Partnership firms  
- Private/Public Limited Companies
- LLPs, Trusts, Societies, NGOs

Required Documents:
- KYC of all authorized signatories
- Business registration proof (GST certificate, Udyam registration, etc.)
- Board resolution / partnership deed for non-individual entities"""
    },
    # ─── Fixed Deposits ───────────────────────────────────────────────────────
    {
        "topic": "fixed_deposit",
        "source": "FD Policy 2025",
        "content": """Fixed Deposit (FD) - Complete Guide

A Fixed Deposit is a secure investment instrument where money is deposited for
a fixed tenure at a pre-agreed interest rate.

Tenures Available: 7 days to 10 years
Minimum Deposit: ₹1,000

Interest Rates (Effective March 2026):
| Tenure          | General | Senior Citizen |
|-----------------|---------|----------------|
| 7 - 29 days     | 3.00%   | 3.50%          |
| 30 - 90 days    | 4.50%   | 5.00%          |
| 91 - 180 days   | 5.75%   | 6.25%          |
| 181 - 364 days  | 6.50%   | 7.00%          |
| 1 year          | 6.75%   | 7.25%          |
| 1-2 years       | 7.00%   | 7.50%          |
| 2-3 years       | 7.10%   | 7.60%          |
| 3-5 years       | 6.90%   | 7.40%          |
| 5-10 years      | 6.50%   | 7.00%          |

Tax-Saving FD (Sec 80C): 5-year lock-in, ₹1.5 lakh/year deduction limit
Premature Withdrawal Penalty: 1% reduction on applicable rate
Loan Against FD: Up to 90% of FD value at FD rate + 2%"""
    },
    {
        "topic": "fixed_deposit",
        "source": "FD Policy 2025",
        "content": """Fixed Deposit - Auto-Renewal and Nomination

Auto-Renewal Policy:
- FDs are auto-renewed at maturity by default unless instructed otherwise
- Renewed at prevailing interest rates on the maturity date
- Customer can opt for: Auto-renew (principal + interest), Auto-renew (principal only), or Encash at maturity
- Instruction must be given 3 days before maturity for changes

Premature Closure Rules:
- FDs closed before 7 days: No interest paid
- FDs closed between 7-29 days: 3% p.a. (irrespective of original rate)
- FDs closed after 30 days: Contracted rate minus 1% penalty
- Emergency premature closure (medical proof): 0.5% penalty instead of 1%

Nomination and Inheritance:
- Maximum 1 nominee per FD (joint FDs: nominee is payable on death of all holders)
- Nominee can be added/changed anytime during FD tenure
- In case of depositor's demise, nominee can claim FD proceeds within 1 year post-maturity"""
    },
    # ─── Loans ───────────────────────────────────────────────────────────────
    {
        "topic": "home_loan",
        "source": "Loan Products Guide 2025",
        "content": """Home Loan - Eligibility, Rates, and Features

Home Loan allows customers to purchase or construct residential properties.

Eligibility Criteria:
- Age: 21 to 65 years (at loan maturity)
- Employment: Salaried (min 2 years), Self-employed (min 3 years business vintage)
- Minimum income: ₹25,000/month (metro); ₹15,000/month (non-metro)
- CIBIL score: Minimum 700 recommended (750+ for best rates)
- No existing loan defaults or NPA history

Loan Amount:
- Minimum: ₹5 lakh
- Maximum: ₹5 crore (higher for premium customers)
- LTV (Loan-to-Value): Up to 80% of property value (90% for loans below ₹30 lakh)

Interest Rates (Floating, EBLR-linked):
- CIBIL 750+, income ₹1L+: EBLR + 0.15% = ~8.40% p.a.
- CIBIL 700-750: EBLR + 0.65% = ~8.90% p.a.
- CIBIL below 700: EBLR + 1.20% = ~9.45% p.a.
- Fixed rate option: 9.75% p.a. for first 3 years, then floating

Tenure: Up to 30 years
Processing fee: 0.5% of loan amount (min ₹5,000, max ₹25,000)

Required Documents:
- Identity proof (Aadhaar, PAN)
- Address proof
- Income proof (3 months salary slips / 2 years ITR)
- Bank statements (6 months)
- Property documents (sale agreement, NOC, title deed)
- Form 16 / Business P&L (for self-employed)"""
    },
    {
        "topic": "personal_loan",
        "source": "Loan Products Guide 2025",
        "content": """Personal Loan - Quick Unsecured Credit

Personal loans are multi-purpose unsecured loans for individuals.

Eligibility:
- Age: 21 to 60 years
- Salaried: Minimum take-home ₹20,000/month; employed for at least 1 year with current employer
- Self-employed: Minimum net profit ₹3 lakh/year; 2 years business vintage
- CIBIL: Minimum 700 (below 700 may attract higher rates or rejection)
- Existing bank relationship (salary account / savings account preferred)

Loan Details:
- Amount: ₹50,000 to ₹25 lakh
- Tenure: 12 to 60 months
- Disbursal time: 24-48 hours (pre-approved), 5-7 days (fresh)

Interest Rates:
- Pre-approved (existing customers): 10.5% to 12% p.a.
- Salaried prime (CIBIL 750+): 12% to 14% p.a.
- Standard salaried (CIBIL 700-750): 14% to 18% p.a.
- Self-employed: 15% to 21% p.a.

Fees:
- Processing fee: 2% of loan amount
- Prepayment: Free after 12 EMIs; 3% penalty within first 12 months
- Late payment: 2% per month on overdue amount

Documents Needed:
- Identity + Address proof
- Latest 2 salary slips
- 3-month bank statement
- Employment letter or appointment letter"""
    },
    {
        "topic": "car_loan",
        "source": "Loan Products Guide 2025",
        "content": """Car Loan / Auto Loan

Vehicle financing for new and used automobiles, two-wheelers, and commercial vehicles.

New Car Loan:
- Funding: Up to 90% on-road price
- Rate: 8.75% - 10.5% p.a. (EBLR-linked)
- Tenure: 12 to 84 months
- Processing fee: ₹3,500 flat

Used Car Loan:
- Funding: Up to 75% of car value (bank-assessed)
- Max vehicle age at maturity: 10 years
- Rate: 12% - 15% p.a.
- Tenure: 12 to 60 months

Two-Wheeler Loan:
- Funding: Up to 85% of on-road price
- Rate: 13% - 16% p.a.
- Tenure: 6 to 48 months

Eligibility:
- Age 21-65 years
- Minimum income ₹15,000/month (car); ₹10,000/month (two-wheeler)
- CIBIL 680+ preferred

Required Documents:
- KYC (ID + address proof)
- Income proof
- Quotation from dealer (new vehicle) or RC + valuation report (used)
- Passport-size photograph"""
    },
    {
        "topic": "education_loan",
        "source": "Loan Products Guide 2025",
        "content": """Education Loan

Financing higher education at recognized institutions in India and abroad.

Courses Covered:
- Graduate and post-graduate professional courses (Engineering, MBA, MBBS, etc.)
- Government diploma courses
- Job-oriented courses (nursing, hotel management, etc.)
- Courses from reputed foreign universities (USA, UK, Canada, Australia, etc.)

Loan Limits:
- Studies in India: Up to ₹20 lakh (no collateral up to ₹7.5 lakh)
- Studies abroad: Up to ₹50 lakh (no collateral up to ₹7.5 lakh)

Interest Rates:
- India: 9.5% to 11% p.a.
- Abroad: 10.5% to 12% p.a.
- 0.5% concession for female students
- 1% concession on full interest service during moratorium

Repayment:
- Moratorium period: Course duration + 12 months (or 6 months after first job)
- Repayment tenure: Up to 15 years after moratorium
- Tax benefit: Interest paid is deductible under Section 80E for 8 years

Eligible Expenses:
- Tuition fees, hostel, exam fees, books, equipment, travel (abroad)
- Living expenses (up to 10% of total loan for in-India courses)"""
    },
    # ─── Credit Cards ─────────────────────────────────────────────────────────
    {
        "topic": "credit_card",
        "source": "Cards Division Handbook 2025",
        "content": """Credit Cards - Types, Features, and Benefits

Card Variants:

1. Classic (Starter)
   - Credit limit: ₹20,000 to ₹1 lakh
   - Annual fee: ₹499 (waived on ₹50,000 annual spend)
   - Reward rate: 1 point per ₹100
   - No fuel surcharge waiver

2. Gold
   - Credit limit: ₹1 lakh to ₹3 lakh
   - Annual fee: ₹999 (waived on ₹1 lakh annual spend)
   - Reward rate: 2 points per ₹100 (3x on groceries and dining)
   - 1% fuel surcharge waiver (up to ₹250/month)
   - 1 complimentary airport lounge access/quarter

3. Platinum / Signature
   - Credit limit: ₹3 lakh to ₹10 lakh
   - Annual fee: ₹2,499 (waived on ₹3 lakh annual spend)
   - Reward rate: 5 points per ₹100 on all spends
   - Unlimited lounge access (Visa Signature / Mastercard World)
   - 5% cashback on online shopping (capped at ₹500/month)
   - Concierge service, travel insurance up to ₹50 lakh

4. Business Corporate Card
   - Credit limit: Up to ₹50 lakh (company-based)
   - Detailed expense management reports
   - Separate billing per employee card"""
    },
    {
        "topic": "credit_card",
        "source": "Cards Division Handbook 2025",
        "content": """Credit Card - Charges, Fees, and Default Policy

Interest and Charges:
- Finance charge (if full payment not made): 3.49% per month (41.88% p.a.)
- Minimum payment due: 5% of outstanding or ₹500 (whichever is higher)
- Late payment fee: ₹100 (bill up to ₹500), ₹500 (₹500-₹10,000), ₹1,200 (above ₹10,000)
- Cash advance fee: 3.5% of amount (min ₹500); interest from day 1 (no grace period)
- Overlimit charge: ₹600 per month
- Card replacement: ₹200 (lost/stolen), free (damaged)
- Foreign transaction fee: 3.5% of converted amount

Grace Period:
- Free credit period: Up to 50 days for retail purchases (if previous statement cleared in full)
- No grace period on cash advances

Credit Limit Enhancement:
- Auto-enhancement: Annual review based on spending pattern and payment history
- Manual request: Through net banking or relationship manager
- Temporary enhancement: Available for specific events (travel, wedding), valid 60 days

Reporting Lost/Stolen Card:
- Call 1800-XXX-XXXX (24x7) or block via mobile app immediately
- Liability on fraudulent transactions after reporting: Zero (RBI zero-liability rules)"""
    },
    # ─── Transactions ─────────────────────────────────────────────────────────
    {
        "topic": "transactions",
        "source": "Digital Banking Guide 2025",
        "content": """Fund Transfer Methods - NEFT, RTGS, IMPS, UPI

NEFT (National Electronic Funds Transfer):
- Operates 24x7 (since Dec 2019)
- No minimum; maximum: No cap (but tax reporting if above ₹10 lakh)
- Batch settlements: Every 30 minutes (48 batches/day)
- Charges: Free from all channels (as per RBI mandate since Jan 2020)
- Typically credited within 2 hours on working days

RTGS (Real Time Gross Settlement):
- Available 24x7 for interbank transfers
- Minimum: ₹2 lakh; No maximum cap
- Charges: Free for online; ₹25-50 at branch (for amounts above ₹2 lakh)
- Settlement: Real-time (immediate)
- Primarily used for high-value corporate transactions

IMPS (Immediate Payment Service):
- Available 24x7x365 including holidays
- Minimum: ₹1; Maximum: ₹5 lakh per transaction (NPCI limit)
- Charges: ₹3.5 to ₹15 depending on amount; free via UPI overlay
- Settlement: Immediate
- Requires MMID + Mobile / Account number + IFSC

UPI (Unified Payments Interface):
- Instant 24x7 transfer
- Maximum: ₹1 lakh per transaction (₹2 lakh for verified merchants)
- Daily limit: ₹1 lakh (can be set lower by user)
- Charges: Free for P2P; MDR applicable for P2M above threshold
- Linked to VPA (Virtual Payment Address) — no need to share account number"""
    },
    {
        "topic": "transactions",
        "source": "Digital Banking Guide 2025",
        "content": """Cheque Processing and Dishonour Policy

Cheque Clearing:
- Local cheques (same city): Cleared within T+1 day via MICR/CTS
- Outstation cheques (pre-2019): Cleared within T+2 to T+5 days
- CTS (Cheque Truncation System): Now all-India, speeds up clearing significantly

Cheque Dishonour (Bounce) Charges:
- Cheque returned for insufficient funds: ₹500 + GST per instance (issued by you)
- Inward return (cheque deposited by you bounces): ₹150 + GST

Legal consequences of cheque bounce:
- Negotiable Instruments Act, Section 138: Criminal offense if cheque issued for legal debt
- Payee can send legal notice within 30 days of dishonour
- If not paid within 15 days of notice, payee can file complaint within 30 days
- Penalty: Up to 2 years imprisonment or 2x cheque amount or both

Stop Payment:
- Stop payment request valid for 6 months; renewable
- Stop payment fee: ₹100 per cheque leaf
- Cannot stop payment after cheque is presented and processed"""
    },
    # ─── Internet/Mobile Banking ───────────────────────────────────────────────
    {
        "topic": "digital_banking",
        "source": "Digital Banking Guide 2025",
        "content": """Internet Banking and Mobile Banking Features

Net Banking:
- Account balance and mini-statement (last 25 transactions)
- Fund transfers: NEFT, RTGS, IMPS up to ₹10 lakh/day
- Bill payments: Utility bills, insurance premiums, tax payments
- Fixed Deposit opening, closure, and renewal
- Loan account management and repayment
- Debit/credit card management (block, unblock, PIN change)
- Investment services: Mutual funds, IPO applications

Mobile Banking App Features:
- UPI integration (send/receive money via QR or VPA)
- One-tap balance check
- Video KYC for new account opening
- EMI conversion on credit card purchases
- Instant personal loan (pre-approved customers, 2 minutes disbursal)
- ATM cash withdrawal without card (Cardless cash)
- Split bills and request money features
- Multilingual support (12 languages)

Security Features:
- 2-Factor Authentication (OTP + MPIN)
- Biometric login (fingerprint / Face ID)
- Transaction limits configurable by customer
- Auto-lock after 5 failed PIN attempts
- Session timeout after 5 minutes inactivity
- Real-time SMS/email alerts on all transactions"""
    },
    # ─── KYC and Compliance ───────────────────────────────────────────────────
    {
        "topic": "kyc",
        "source": "Compliance Manual 2025",
        "content": """KYC (Know Your Customer) - Requirements and Process

Mandatory KYC Documents:

Identity Proof (any one):
- Aadhaar Card (with consent for Aadhaar-based KYC)
- Passport
- Voter ID Card
- Driving License
- PAN Card (for accounts with annual transactions above ₹50,000)

Address Proof (any one):
- Aadhaar Card (most widely accepted)
- Passport
- Driving License
- Utility bills (electricity/telephone/gas) - not older than 3 months
- Bank statement of another bank (not older than 3 months)
- Rent agreement (registered) + latest utility bill

KYC Validity and Re-KYC:
- Low risk customers: Re-KYC every 10 years
- Medium risk: Every 8 years
- High risk (PEP, large transaction history): Every 2 years
- Accounts with outdated KYC will be moved to limited-operational status

Digital KYC Options:
- Aadhaar OTP-based eKYC: Fully online; counts as KYC for accounts up to ₹1 lakh limit
- Video KYC: Fully operational account (no limit); needs live video with agent
- CKYC (Central KYC): One-time KYC stored centrally; valid across all financial institutions"""
    },
    {
        "topic": "kyc",
        "source": "Compliance Manual 2025",
        "content": """PAN Card - Requirement and Tax Compliance

PAN Requirement in Banking:
- Opening any new account: PAN mandatory
- Cash deposits above ₹50,000 per day: PAN required
- Time deposits above ₹50,000: PAN needed
- Mutual fund investments above ₹50,000: PAN required
- Purchase of demand draft above ₹50,000: PAN needed
- Form 60/61 alternative: If PAN not available, Form 60 must be submitted

TDS on Banking Transactions:
- Savings account interest above ₹10,000/year (₹50,000 for senior citizens): 10% TDS
- If PAN not submitted, TDS rate becomes 20%
- FD interest TDS: Same threshold as savings; 15H/15G form to avoid TDS if income below exemption limit

Form 15G/15H:
- 15G: For individuals below 60 years with income below taxable limit
- 15H: For senior citizens (60+ years) with income below taxable limit
- Must be submitted at start of each financial year
- Can be submitted online via net banking"""
    },
    # ─── Grievance and Support ─────────────────────────────────────────────────
    {
        "topic": "customer_support",
        "source": "Customer Service Policy 2025",
        "content": """Grievance Redressal - How to Raise and Escalate Complaints

Complaint Channels (Tier 1):
- Mobile App: 'Help & Support' section → 'Raise Complaint'
- Net Banking: Service Request module
- Phone Banking: 1800-XXX-XXXX (toll free, 24x7)
- Branch Visit: Complaint register / Relationship Manager
- Email: customercare@bank.in

Resolution Timelines (as per RBI guidelines):
- Account-related queries: 7 working days
- Card disputes: 7 working days
- Loan-related: 15 working days
- Fraud disputes: 90 days (as per RBI norms)

Escalation (Tier 2 - if unresolved):
- Nodal Officer: nodal.officer@bank.in (must respond within 10 working days)
- Zonal Manager escalation via branch

Banking Ombudsman (Tier 3 - if still unresolved):
- RBI Banking Ombudsman: cms.rbi.org.in
- Eligible if: Bank failed to resolve within 30 days, or resolution unsatisfactory
- No fee for filing complaint
- BO can award up to ₹20 lakh in certain complaint categories"""
    },
    {
        "topic": "customer_support",
        "source": "Customer Service Policy 2025",
        "content": """Account Status Queries - Balance, Statement, and Transaction Disputes

Checking Account Balance:
- Mobile App / Net Banking: Real-time balance
- ATM: Balance enquiry (free, unlimited)
- Missed call (dedicated number): Automated balance on SMS within 30 seconds
- SMS banking: Send 'BAL <last 4 digits>' to shortcode
- Phone banking IVR: 24x7 automated

Account Statement:
- Passbook update: At any bank branch or kiosk (free)
- PDF statement via email: Last 12 months free via net banking
- Physical statement by courier: ₹100 per request
- Certified statement: ₹200 per request (bank stamp + signature)

Transaction Dispute Process:
1. Report within 3 days for UPI/NEFT/IMPS disputes
2. For ATM cash not dispensed but debited: Report to bank within 7 days
   - If not resolved in 5 working days, ₹100/day compensation applies
3. For unauthorized card transactions: Report immediately, bank must resolve in 90 days
4. Charge back for credit card: File dispute via app or contact card centre within 120 days of transaction"""
    },
    # ─── Loans - Eligibility / Repayment ─────────────────────────────────────
    {
        "topic": "loan_eligibility",
        "source": "Credit Underwriting Policy 2025",
        "content": """Loan Eligibility - CIBIL Score and Credit Assessment

CIBIL Score Importance:
- Score Range: 300 to 900 (higher is better)
- 750-900: Excellent - Best rates, faster approval
- 700-749: Good - Standard rates, normal processing
- 650-699: Fair - Higher rates, additional documents may be needed
- Below 650: Poor - High rejection risk, collateral/guarantor may be required

How CIBIL Score is Affected:
- Payment history: 35% impact (most critical - never delay EMIs)
- Credit utilization: 30% impact (keep credit card usage below 30%)
- Credit age: 15% impact (older accounts are better)
- New credit enquiries: 10% (too many applications drop score)
- Credit mix: 10% (mix of secured and unsecured is good)

Improving CIBIL Score:
- Pay all EMIs and credit card bills on time (set auto-debit)
- Keep credit card utilization below 30% of limit
- Avoid multiple loan applications in short period
- Do not close old credit cards or long-standing accounts
- Check CIBIL report annually for errors (free via RBI-mandated channels)

Debt-to-Income (FOIR) Norms:
- FOIR (Fixed Obligation to Income Ratio): Total EMIs / Gross Monthly Income
- Bank's maximum FOIR: 50-55% for home loans; 40-45% for personal loans
- Example: Income ₹50,000/month, existing EMI ₹10,000 → FOIR 20%; eligible for additional EMI up to ₹15,000-17,500"""
    },
    {
        "topic": "loan_repayment",
        "source": "Credit Underwriting Policy 2025",
        "content": """Loan Repayment - EMI, Prepayment, and Foreclosure

EMI (Equated Monthly Installment):
- EMI = P × r × (1+r)^n / ((1+r)^n - 1)
  where P = Principal, r = Monthly interest rate, n = Months
- EMI due date: Same as disbursement date each month
- Auto-debit from linked account: Recommended

Prepayment Options:
- Part prepayment: Reduces tenure or reduces EMI (customer choice)
- Prepayment charges (floating rate loans): ZERO as per RBI guidelines
- Prepayment charges (fixed rate loans): 2% of prepaid amount (within 2 years)
- After 2 years for fixed rate: 1% of prepaid amount

Foreclosure (Full Prepayment):
- Home loan (floating): No penalty (RBI directive)
- Personal loan: 3% of outstanding if within 12 months; 2% after 12 months
- Car loan: 5% if foreclosed within 6 months; NIL after 12 months
- Education loan: NIL penalty at any point

EMI Bounce and Overdue:
- 1st bounce: Bank waives charges as courtesy
- 2nd+ bounce: ₹500 + GST per bounce
- Overdue interest: 2-3% p.a. additional on outstanding amount
- 90 days overdue → Account classified as NPA (Non-Performing Asset)
- NPA impacts CIBIL score severely; legal action may be initiated"""
    },
    # ─── Debit Cards and ATM ──────────────────────────────────────────────────
    {
        "topic": "debit_card",
        "source": "Cards Division Handbook 2025",
        "content": """Debit Cards - Features, Limits, and Security

Debit Card Variants:
1. Classic Visa/RuPay: ATM-only usage, limited online
2. Platinum Debit: Full POS + online, higher daily limits
3. Business Debit: High limits, expense tracking, no foreign currency restriction

Daily Transaction Limits:
- ATM withdrawal: ₹20,000 (Classic), ₹50,000 (Platinum), ₹1,00,000 (Business)
- POS/Online: ₹1,00,000 (Classic), ₹5,00,000 (Platinum)
- International: Disabled by default; enable via mobile app or branch

ATM Charges:
- Own bank ATMs: 5 free transactions per month; ₹20 per transaction after
- Other bank ATMs (metro): 3 free transactions per month; ₹20 after
- Other bank ATMs (non-metro): 5 free transactions per month; ₹20 after
- International ATM: ₹150 per transaction + forex markup

Security:
- EMV chip + PIN (no magnetic stripe fallback since 2022)
- Contactless (NFC) up to ₹5,000 without PIN
- Freeze/unfreeze via mobile app instantly
- Virtual debit card for online transactions (no physical card needed)
- Transaction alerts: SMS for every debit ₹5,000+; email for all"""
    },
    # ─── International Banking ─────────────────────────────────────────────────
    {
        "topic": "international_banking",
        "source": "Forex and International Banking Guide 2025",
        "content": """Forex and International Banking Services

Foreign Currency Accounts:
- FCNR (B): For NRIs; deposits in USD, EUR, GBP, JPY, AUD, CAD
  - Fully repatriable; interest tax-free in India
  - Minimum deposit: USD 1,000; Tenure 1-5 years
- NRE Savings: Rupee account; principal + interest fully repatriable; tax-free
- NRO Savings: Rupee account; earnings from India; partial repatriation (up to $1 million/year)

Forex Card (Travel Card):
- Pre-loaded multi-currency card
- Rates locked at loading time (shield against fluctuations)
- Accepted in 150+ countries
- Reload online anytime
- Insurance: Up to ₹5 lakh for loss/theft

International Wire Transfer (SWIFT):
- Outward remittance: LRS limit of $250,000/year per individual
- TCS on remittances above ₹7 lakh (5% for education/medical; 20% for others from FY2023-24)
- Inward remittance: No limit; FEMA compliance required above $10,000
- Charges: ₹500-₹2,000 per transaction (depends on amount and currency)

RBI Liberalised Remittance Scheme (LRS):
- Resident individuals can remit up to $250,000/year abroad
- Purpose: Education, medical, travel, investments, gifts, maintenance of relatives abroad
- PAN mandatory for LRS transactions"""
    },
    # ─── Insurance and Investments ─────────────────────────────────────────────
    {
        "topic": "insurance_investments",
        "source": "Wealth Management Guide 2025",
        "content": """Bancassurance and Investment Products

Life Insurance (Through Bank Partners):
- Term Insurance: Pure protection, sum assured ₹10 lakh to ₹5 crore
- Endowment / Money Back: Savings + protection combo
- ULIP: Market-linked returns + insurance; lock-in 5 years
- Group Credit Life Insurance: Covers loan outstanding in case of borrower's death

General Insurance:
- Home Insurance: Structure + contents; customizable
- Vehicle Insurance: Third-party mandatory; comprehensive optional
- Health Insurance: Hospitalization, OPD, critical illness riders
- Travel Insurance: Trip cancellation, medical emergency abroad

Mutual Funds (through bank's AMFI-registered platform):
- SIP starting from ₹500/month
- Liquid/Debt funds: 6-8% expected returns; lower risk
- Balanced/Hybrid: 8-11%; moderate risk
- Equity Funds: 10-15% long-term; higher risk
- Tax saving ELSS: 3-year lock-in; eligible for 80C deduction

Government Savings Schemes (available at bank):
- PPF: 7.1% p.a.; 15-year lock-in; tax-free returns
- Sukanya Samriddhi Yojana: 8.2% p.a.; for girl child below 10 years
- NSC (National Savings Certificate): 7.7% p.a.; 5-year term
- Senior Citizen Savings Scheme (SCSS): 8.2% p.a.; 5-year; ₹30 lakh max"""
    },
]


def generate_doc_id(content: str, metadata: dict) -> str:
    """Generate a stable document ID from content hash."""
    data = json.dumps({"content": content[:100], **metadata}, sort_keys=True)
    return hashlib.md5(data.encode()).hexdigest()


def ingest_banking_faq():

    # ── Step 2: Initialize ChromaDB ───────────────────────────────────────────
    logger.info(f"Initializing ChromaDB at: {CHROMA_DB_PATH}")
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    # Delete existing collection to allow re-ingestion
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
        logger.info(f"Deleted existing collection: {COLLECTION_NAME}")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    # ── Step 3: Text Splitting ─────────────────────────────────────────────────
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    all_chunks = []
    all_metadatas = []
    all_ids = []

    for item in BANKING_FAQ_DATA:
        chunks = splitter.split_text(item["content"])
        for i, chunk in enumerate(chunks):
            meta = {
                "topic": item["topic"],
                "source": item["source"],
                "chunk_index": i,
            }
            doc_id = generate_doc_id(chunk, meta)
            all_chunks.append(chunk)
            all_metadatas.append(meta)
            all_ids.append(doc_id)

    logger.info(f"Split {len(BANKING_FAQ_DATA)} documents into {len(all_chunks)} chunks.")

    # ── Step 4: Embed & Store ─────────────────────────────────────────────────
    BATCH_SIZE = 50
    total_stored = 0

    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch_chunks = all_chunks[i:i + BATCH_SIZE]
        batch_meta = all_metadatas[i:i + BATCH_SIZE]
        batch_ids = all_ids[i:i + BATCH_SIZE]

        logger.info(f"Embedding batch {i // BATCH_SIZE + 1} ({len(batch_chunks)} chunks)...")
        try:
            embeddings = embedding_model.embed_documents(batch_chunks)
            collection.add(
                documents=batch_chunks,
                embeddings=embeddings,
                metadatas=batch_meta,
                ids=batch_ids,
            )
            total_stored += len(batch_chunks)
            logger.info(f"  ✅ Stored {len(batch_chunks)} chunks (total: {total_stored})")
        except Exception as e:
            logger.error(f"  ❌ Failed batch {i // BATCH_SIZE + 1}: {e}")
            raise

    logger.info(f"\n✅ Ingestion complete! Stored {total_stored} chunks in ChromaDB collection '{COLLECTION_NAME}'.")
    return total_stored


if __name__ == "__main__":
    ingest_banking_faq()
