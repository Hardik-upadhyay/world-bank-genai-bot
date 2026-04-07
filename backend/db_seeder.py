"""
db_seeder.py - World Bank AI Assistant Database Seeder
========================================================
Wipes and re-seeds all banking tables with rich sample data:
  - 1 Bank Manager
  - 5 Customers (diverse profiles, currencies, KYC statuses)
  - 2 accounts per customer (different types)
  - 10-15 realistic dated transactions per account

Usage (run from the backend/ directory):
    python db_seeder.py           # wipe + reseed users/accounts/transactions
    python db_seeder.py --full    # also wipe chat_sessions and chat_messages
"""
import sys
import random
import string
import argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.database import init_db, get_connection
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Helpers ────────────────────────────────────────────────────────────────────

def random_ref() -> str:
    return "REF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


def dt(days_ago: int, hour: int = 10, minute: int = 0) -> str:
    """Return an ISO datetime string N days in the past."""
    d = datetime(2026, 3, 27, hour, minute) - timedelta(days=days_ago)
    return d.strftime("%Y-%m-%d %H:%M:%S")


# ── Seed Data ──────────────────────────────────────────────────────────────────

MANAGER = {
    "username": "manager",
    "password": "manager123",
    "full_name": "James Wilson",
    "email": "james.wilson@worldbank.org",
}

CUSTOMERS = [
    {
        "username": "alice",
        "password": "alice123",
        "full_name": "Alice Chen",
        "email": "alice.chen@example.com",
        "customer_id": "WB-CUST-001",
        "phone": "+1-555-0101",
        "address": "42 Maple Street, Washington DC 20001, USA",
        "date_of_birth": "1990-06-15",
        "kyc_status": "Verified",
        "accounts": [
            {
                "type": "Savings",
                "balance": 24750.00,
                "currency": "USD",
                "branch": "Washington HQ",
                "status": "Active",
                "opened_date": "2022-01-15",
                "transactions": [
                    ("credit", 5000.00, "Salary credit - March 2026",     1),
                    ("debit",  1200.00, "Rent payment - March 2026",       3),
                    ("credit",  250.00, "Interest credit Q1 2026",         5),
                    ("debit",   450.75, "Utility bills - Feb 2026",        8),
                    ("credit", 3000.00, "Wire transfer received",          10),
                    ("debit",   800.00, "Online shopping - Amazon",        12),
                    ("debit",   120.50, "Health insurance premium",        15),
                    ("credit",  500.00, "Freelance consulting income",     18),
                    ("debit",   200.00, "Grocery - Whole Foods",           20),
                    ("credit", 5000.00, "Salary credit - Feb 2026",        32),
                ],
            },
            {
                "type": "Fixed Deposit",
                "balance": 50000.00,
                "currency": "USD",
                "branch": "Washington HQ",
                "status": "Active",
                "opened_date": "2023-06-01",
                "transactions": [
                    ("credit", 50000.00, "Fixed Deposit opening amount",   60),
                    ("credit",   312.50, "Interest credit - Q4 2025",      90),
                    ("credit",   312.50, "Interest credit - Q3 2025",     180),
                ],
            },
        ],
    },
    {
        "username": "rahul",
        "password": "rahul123",
        "full_name": "Rahul Sharma",
        "email": "rahul.sharma@example.com",
        "customer_id": "WB-CUST-002",
        "phone": "+91-98765-43210",
        "address": "15 MG Road, New Delhi 110001, India",
        "date_of_birth": "1985-11-22",
        "kyc_status": "Verified",
        "accounts": [
            {
                "type": "Current",
                "balance": 125000.00,
                "currency": "USD",
                "branch": "New Delhi Office",
                "status": "Active",
                "opened_date": "2021-03-10",
                "transactions": [
                    ("credit", 20000.00, "Business revenue - March 2026",  2),
                    ("debit",  8500.00,  "Vendor payment - Infosys",        4),
                    ("debit",  3200.00,  "Office rent - March 2026",        6),
                    ("credit", 15000.00, "Client invoice payment",          9),
                    ("debit",  1200.00,  "Software subscriptions",          11),
                    ("debit",   450.00,  "Electricity bill",                14),
                    ("credit", 20000.00, "Business revenue - Feb 2026",    33),
                    ("debit",  8500.00,  "Vendor payment - TCS",           35),
                    ("credit",  5000.00, "GST refund",                     40),
                    ("debit",  2500.00,  "Travel expenses",                 45),
                ],
            },
            {
                "type": "Savings",
                "balance": 8420.50,
                "currency": "USD",
                "branch": "New Delhi Office",
                "status": "Active",
                "opened_date": "2021-03-10",
                "transactions": [
                    ("credit", 1000.00, "Monthly savings transfer",         7),
                    ("credit",   52.63, "Interest credit Q1 2026",         10),
                    ("credit", 1000.00, "Monthly savings transfer",        37),
                    ("credit",   48.20, "Interest credit Q4 2025",         97),
                ],
            },
        ],
    },
    {
        "username": "sofia",
        "password": "sofia123",
        "full_name": "Sofía Martínez",
        "email": "sofia.martinez@example.com",
        "customer_id": "WB-CUST-003",
        "phone": "+52-55-1234-5678",
        "address": "Av. Reforma 222, Mexico City 06600, Mexico",
        "date_of_birth": "1992-03-08",
        "kyc_status": "Verified",
        "accounts": [
            {
                "type": "Savings",
                "balance": 15300.75,
                "currency": "USD",
                "branch": "Mexico City Office",
                "status": "Active",
                "opened_date": "2023-01-20",
                "transactions": [
                    ("credit", 3500.00, "Salary credit - March 2026",       1),
                    ("debit",   900.00, "Apartment rent",                    3),
                    ("debit",   150.00, "Internet + phone bill",             5),
                    ("credit",   75.00, "Interest credit Q1 2026",           7),
                    ("credit", 3500.00, "Salary credit - Feb 2026",         32),
                    ("debit",   420.00, "Flight ticket - CDMX to NY",       36),
                    ("debit",   280.00, "Supermarket - Walmart",            40),
                ],
            },
            {
                "type": "Current",
                "balance": 4200.00,
                "currency": "USD",
                "branch": "Mexico City Office",
                "status": "Active",
                "opened_date": "2023-08-15",
                "transactions": [
                    ("credit", 4000.00, "Initial deposit",                  90),
                    ("credit",   500.00, "Freelance project payment",        20),
                    ("debit",   300.00, "Professional training fee",         25),
                ],
            },
        ],
    },
    {
        "username": "priya",
        "password": "priya123",
        "full_name": "Priya Nair",
        "email": "priya.nair@example.com",
        "customer_id": "WB-CUST-004",
        "phone": "+91-94450-12345",
        "address": "12 Bandra West, Mumbai 400050, India",
        "date_of_birth": "1995-07-19",
        "kyc_status": "Pending",
        "accounts": [
            {
                "type": "Savings",
                "balance": 6800.00,
                "currency": "USD",
                "branch": "Mumbai Office",
                "status": "Active",
                "opened_date": "2024-11-01",
                "transactions": [
                    ("credit", 2500.00, "Salary credit - March 2026",       2),
                    ("debit",   600.00, "PG accommodation rent",             4),
                    ("debit",   120.00, "Electricity and water",             8),
                    ("credit", 2500.00, "Salary credit - Feb 2026",         33),
                    ("debit",   450.00, "Online courses - Coursera",        38),
                ],
            },
            {
                "type": "Fixed Deposit",
                "balance": 10000.00,
                "currency": "USD",
                "branch": "Mumbai Office",
                "status": "Active",
                "opened_date": "2024-12-01",
                "transactions": [
                    ("credit", 10000.00, "Fixed Deposit opened",           115),
                    ("credit",    62.50, "Interest credit - Q4 2025",       90),
                ],
            },
        ],
    },
    {
        "username": "chen",
        "password": "chen123",
        "full_name": "Wei Chen",
        "email": "wei.chen@example.com",
        "customer_id": "WB-CUST-005",
        "phone": "+86-138-0013-8000",
        "address": "88 Nanjing Road, Shanghai 200001, China",
        "date_of_birth": "1980-02-14",
        "kyc_status": "Verified",
        "accounts": [
            {
                "type": "Current",
                "balance": 87500.00,
                "currency": "USD",
                "branch": "Shanghai Office",
                "status": "Active",
                "opened_date": "2020-05-01",
                "transactions": [
                    ("credit", 30000.00, "Export revenue - March 2026",     1),
                    ("debit",  12000.00, "Supplier payment - Shenzhen",      3),
                    ("debit",   3500.00, "Logistics & freight charges",       5),
                    ("credit", 15000.00, "Trade receivable settlement",       7),
                    ("debit",   2200.00, "Office utilities Q1 2026",         10),
                    ("credit", 30000.00, "Export revenue - Feb 2026",        32),
                    ("debit",  12000.00, "Supplier payment - Guangzhou",     34),
                    ("debit",   1800.00, "Bank charges and fees",            40),
                    ("credit",   450.00, "Interest credit Q1 2026",         12),
                    ("debit",   5000.00, "Staff salaries - partial",        14),
                ],
            },
            {
                "type": "Savings",
                "balance": 22000.00,
                "currency": "USD",
                "branch": "Shanghai Office",
                "status": "Active",
                "opened_date": "2020-05-01",
                "transactions": [
                    ("credit",  5000.00, "Transfer from Current",            15),
                    ("credit",   137.50, "Interest credit Q1 2026",         12),
                    ("credit",  5000.00, "Transfer from Current",            45),
                    ("credit",   125.00, "Interest credit Q4 2025",         95),
                ],
            },
        ],
    },
]


# ── Seeder ─────────────────────────────────────────────────────────────────────

def seed(wipe_chat: bool = False):
    print("=" * 55)
    print("  World Bank DB Seeder")
    print("=" * 55)
    print("\n[1/3] Initializing database schema...")
    init_db()

    conn = get_connection()
    try:
        cur = conn.cursor()

        # ── Wipe existing banking data ─────────────────────────────
        print("[2/3] Clearing existing data...")
        cur.execute("DELETE FROM transactions")
        cur.execute("DELETE FROM accounts")
        cur.execute("DELETE FROM customers")
        # chat_sessions/chat_messages FK-reference users, so must be deleted before users.
        # When not --full, we re-insert the same users so history becomes orphaned → clean up too.
        cur.execute("DELETE FROM chat_messages")
        cur.execute("DELETE FROM chat_sessions")
        cur.execute("DELETE FROM users")
        conn.commit()
        if wipe_chat:
            print("      All tables cleared (including chat history).")
        else:
            print("      Banking tables cleared (chat history also cleared due to user re-seed).")

        # ── Manager ────────────────────────────────────────────────
        print("[3/3] Seeding data...")
        cur.execute(
            "INSERT INTO users (username, password_hash, role, full_name, email) VALUES (?, ?, 'manager', ?, ?)",
            (
                MANAGER["username"],
                pwd_ctx.hash(MANAGER["password"]),
                MANAGER["full_name"],
                MANAGER["email"],
            ),
        )
        manager_id = cur.lastrowid
        print(f"\n  [OK] Manager  : {MANAGER['username']} / {MANAGER['password']}")

        # ── Customers ──────────────────────────────────────────────
        for c in CUSTOMERS:
            # User row
            cur.execute(
                "INSERT INTO users (username, password_hash, role, full_name, email) VALUES (?, ?, 'customer', ?, ?)",
                (c["username"], pwd_ctx.hash(c["password"]), c["full_name"], c["email"]),
            )
            user_id = cur.lastrowid

            # Customer profile
            cur.execute(
                """INSERT INTO customers
                   (user_id, customer_id, phone, address, date_of_birth, kyc_status, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    c["customer_id"],
                    c["phone"],
                    c["address"],
                    c.get("date_of_birth", ""),
                    c.get("kyc_status", "Verified"),
                    manager_id,
                ),
            )
            cust_db_id = cur.lastrowid

            # Accounts + Transactions
            for acc in c["accounts"]:
                acc_no = "WB" + "".join(random.choices(string.digits, k=10))
                cur.execute(
                    """INSERT INTO accounts
                       (customer_id, account_number, account_type, balance, currency, branch, status, opened_date)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        cust_db_id,
                        acc_no,
                        acc["type"],
                        acc["balance"],
                        acc["currency"],
                        acc["branch"],
                        acc.get("status", "Active"),
                        acc.get("opened_date", "2024-01-01"),
                    ),
                )
                acc_id = cur.lastrowid

                # Running balance for balance_after calculation
                running = acc["balance"]
                # Transactions are defined oldest → reverse for accurate running balance
                txns = acc.get("transactions", [])
                # Sort by days_ago descending so we run oldest to newest
                txns_sorted = sorted(txns, key=lambda x: x[3], reverse=True)
                # Compute starting balance (reverse all txns from current balance)
                start_bal = acc["balance"]
                for txn_type, amount, _, _ in txns_sorted:
                    if txn_type == "credit":
                        start_bal -= amount
                    else:
                        start_bal += amount

                running = start_bal
                for txn_type, amount, desc, days_ago in txns_sorted:
                    if txn_type == "credit":
                        running += amount
                    else:
                        running -= amount
                    cur.execute(
                        """INSERT INTO transactions
                           (account_id, type, amount, currency, description, date, reference_no, balance_after)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            acc_id,
                            txn_type,
                            amount,
                            acc["currency"],
                            desc,
                            dt(days_ago, hour=random.randint(8, 18), minute=random.randint(0, 59)),
                            random_ref(),
                            round(running, 2),
                        ),
                    )

            kyc_label = f"[KYC: {c.get('kyc_status', 'Verified')}]"
            print(f"  [OK] Customer : {c['username']:<10} / {c['password']:<12}  {c['full_name']}  {kyc_label}")

        conn.commit()

        print("\n" + "=" * 55)
        print("  Seeding complete!")
        print("=" * 55)
        print("\nCredentials summary:")
        print(f"  {'Role':<10} {'Username':<12} {'Password':<14} Name")
        print(f"  {'-'*10} {'-'*12} {'-'*14} {'-'*25}")
        print(f"  {'Manager':<10} {'manager':<12} {'manager123':<14} James Wilson")
        for c in CUSTOMERS:
            print(f"  {'Customer':<10} {c['username']:<12} {c['password']:<14} {c['full_name']}")

    except Exception as e:
        conn.rollback()
        print(f"\n[FAIL] Seeding failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the World Bank SQLite database.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Also wipe chat_sessions and chat_messages (default: preserve chat history)",
    )
    args = parser.parse_args()
    seed(wipe_chat=args.full)
