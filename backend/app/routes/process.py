"""
Process Route – Hybrid AI Banking Assistant
---------------------------------------------
Handles all chat queries (authenticated AND unauthenticated) with:
  1. Optional JWT authentication — guests get RAG-only answers;
     logged-in customers also get their personal account data.
  2. Language detection + English translation for RAG
  3. Auto-routing: personal queries (logged-in) → SQLite + RAG
                   personal queries (guest)      → polite login prompt
                   general queries               → RAG
  4. 3-tier LLM fallback chain
  5. Response in user's original language
"""
import json
import re
import logging
import base64
import io
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from app.services.llm_service import LLMService, get_llm_service
from app.services.rag_service import RAGService, get_rag_service
from app.auth.auth_service import CurrentUser, decode_access_token
from app.db import queries as db
from app.db.queries import get_user_by_id

router = APIRouter()
logger = logging.getLogger(__name__)

# HTTPBearer with auto_error=False so missing tokens don't raise 401
_bearer = HTTPBearer(auto_error=False)

# ── Prompts ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert AI Banking Assistant exclusively for **The World Bank**.
You ONLY answer questions about The World Bank's own products, services, policies, and customer data.

STRICT RULES:
1. SCOPE — Only answer questions that relate to The World Bank's products, services, policies, fees, rates, procedures, or the logged-in customer's own account data. This is non-negotiable.
2. OTHER BANKS — If the user asks about any other bank (e.g., HDFC, SBI, Chase, Barclays, ICICI, etc.), politely decline and redirect them to The World Bank's equivalent offering. Never provide information about competitor banks.
3. CUSTOMER DATA — For customer-specific data: use ONLY the structured data provided. Do not fabricate account numbers, balances, or transaction details.
4. KNOWLEDGE BASE — For general banking questions: use ONLY the provided knowledge base context about The World Bank's own policies.
5. UNAVAILABLE INFO — If information is not available in the provided context, say so clearly and suggest contacting World Bank support. Do not guess or hallucinate.
6. TONE — Be professional, empathetic, and concise. Use bullet points where helpful.
7. LANGUAGE — Respond in the EXACT SAME LANGUAGE as the customer's original question.
8. PRIVACY — Never reveal other customers' data under any circumstances.
9. CITATIONS — Cite relevant World Bank policy sources when answering general questions.
10. TABLE FORMAT — Whenever the response includes a list of items (transactions, accounts, fees, rates, documents, products, etc.), you MUST present them as a properly formatted GFM markdown table with a header row and separator row (e.g., | Col1 | Col2 | ... |\\n|---|---| ... |). Never use a numbered list or bullet list for structured data that has 2+ attributes per item. This applies to: transaction lists, account lists, fee schedules, rate comparisons, document checklists with more than one column, and any other repeating structured data.

If a question is outside The World Bank's scope, respond like:
"I'm only able to assist with The World Bank's own products and services. For questions about other financial institutions, please contact them directly. Is there anything I can help you with regarding your World Bank account or our offerings?" """

LANGUAGE_DETECT_PROMPT = """Detect the language and translate to English.
Output ONLY this JSON (no markdown, no extra text):
{{"detected_language": "<language>", "english_translation": "<english query>"}}
User query: {query}"""

PERSONAL_QUERY_KEYWORDS = [
    "my account", "my balance", "my transaction", "my loan", "my card",
    "how much", "account number", "statement", "transfer history",
    "my profile", "my details", "my deposit", "last transaction",
    "recent transaction", "last 5", "last 3", "last 10", "last few",
    "transaction history", "my spending", "my payment", "my transfer",
    "what did i", "when did i", "show me my", "list my",
    "मेरा खाता", "मेरा बैलेंस", "शेष राशि",  # Hindi
    "mi cuenta", "mi saldo", "mi balance",      # Spanish
]

# These terms in ANY logged-in user query → always use real customer data
FINANCIAL_KEYWORDS = [
    "transaction", "transactions", "balance", "account", "accounts",
    "transfer", "deposit", "withdrawal", "statement", "payment",
    "credit", "debit", "loan", "card", "spending", "income",
    "recent", "latest", "show me", "list", "history",
]

LOGIN_REQUIRED_RESPONSE = (
    "🔐 **Login Required**\n\n"
    "To access your personal account details — including balances, transactions, "
    "loan status, and account statements — please **log in** to your World Bank account.\n\n"
    "Once logged in, I can give you precise, real-time information about your accounts. "
    "For general banking questions, feel free to ask me anytime!"
)


def _is_content_blocked(exc: Exception) -> bool:
    """Return True when the MaaS gateway blocked the request with a 403 content-safety error."""
    msg = str(exc)
    return "403" in msg and ("Content blocked" in msg or "content_blocked" in msg or "content blocked" in msg.lower())


def is_personal_query(english_query: str) -> bool:
    """Detect if the query is about the user's personal account data."""
    q_lower = english_query.lower()
    if any(kw in q_lower for kw in PERSONAL_QUERY_KEYWORDS):
        return True
    return bool(re.search(r"\bmy\b|\bme\b", q_lower))


def is_financial_query(english_query: str) -> bool:
    """Detect if a query touches any financial/account topic (broader than personal)."""
    q_lower = english_query.lower()
    return any(kw in q_lower for kw in FINANCIAL_KEYWORDS)


def _detect_and_translate(question: str, llm: LLMService) -> tuple[str, str]:
    """Returns (detected_language, english_query). Fallback = English."""
    try:
        msgs = [
            SystemMessage(content="Respond ONLY with valid JSON. No markdown."),
            HumanMessage(content=LANGUAGE_DETECT_PROMPT.format(query=question)),
        ]
        response_text, _ = llm.fallback_chain_call(msgs)
        cleaned = re.sub(r"```[a-z]*\n?", "", response_text).strip()
        data = json.loads(cleaned)
        return data.get("detected_language", "English"), data.get("english_translation", question)
    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
        return "English", question


def _build_customer_context(user_id: int) -> str:
    """Fetch customer data from SQLite and format as structured context for the LLM."""
    profile = db.get_customer_profile(user_id)
    accounts = db.get_accounts(user_id)
    transactions = db.get_transactions(user_id, limit=20)   # fetch up to 20 for full context
    summary = db.get_account_summary(user_id)

    if not profile:
        return ""

    ctx = f"""## Customer Profile
- **Name**: {profile['full_name']}
- **Customer ID**: {profile['customer_id']}
- **Email**: {profile.get('email', 'N/A')}
- **Phone**: {profile.get('phone', 'N/A')}
- **KYC Status**: {profile.get('kyc_status', 'Verified')}

## Accounts Summary
- **Total Accounts**: {summary['account_count']}
- **Total Balance**: {summary['total_balance']:,.2f} (sum across all accounts)

## Account Details
"""
    for acc in accounts:
        curr = acc.get('currency', 'USD')
        ctx += (
            f"- **{acc['account_type']}** | No: {acc['account_number']} "
            f"| Balance: {acc['balance']:,.2f} {curr} "
            f"| Status: {acc['status']} | Branch: {acc.get('branch', 'N/A')}\n"
        )

    total_txns = len(transactions)
    if transactions:
        ctx += f"\n## Transaction History (showing {total_txns} most recent, sorted newest-first)\n"
        ctx += "IMPORTANT: These are the ONLY transactions that exist for this customer. Do not invent or assume any others.\n"
        for i, txn in enumerate(transactions, 1):
            txn_type = txn.get("type", "").lower()
            sign = "+" if txn_type == "credit" else "-"
            curr = txn.get("currency", accounts[0].get("currency", "USD") if accounts else "USD")
            date_str = (txn.get('date') or '')[:10]
            ctx += (
                f"{i}. [{date_str}] {sign}{txn['amount']:,.2f} {curr} "
                f"— {txn.get('description', 'N/A')} "
                f"| Type: {txn_type.capitalize()} "
                f"| Account: {txn.get('account_type', 'N/A')} ({txn.get('account_number', 'N/A')}) "
                f"| Ref: {txn.get('reference_no', 'N/A')}\n"
            )
    else:
        ctx += "\n## Transaction History\nNo transactions found for this customer.\n"

    return ctx


# ── Optional auth dependency ───────────────────────────────────────────────────

def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[CurrentUser]:
    """Returns a CurrentUser if a valid JWT is present, otherwise None (guest)."""
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    user_id = int(payload.get("sub", 0))
    user = get_user_by_id(user_id)
    if not user:
        return None
    return CurrentUser(
        user_id=user_id,
        role=payload.get("role", ""),
        full_name=payload.get("full_name", ""),
        username=user["username"],
    )


# ── Request / Response Models ──────────────────────────────────────────────────

class ConversationTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class BankingChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_history: Optional[list[ConversationTurn]] = Field(default=[])


class SourceCitation(BaseModel):
    source: str
    topic: str
    excerpt: str
    relevance_score: float


class BankingChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    model_used: str
    rag_context_found: bool
    question: str
    detected_language: str
    query_type: str   # "personal" | "general" | "personal_guest"


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("", response_model=BankingChatResponse)
async def banking_assistant(
    request: BankingChatRequest,
    current_user: Optional[CurrentUser] = Depends(get_optional_user),
    llm: LLMService = Depends(get_llm_service),
    rag: RAGService = Depends(get_rag_service),
):
    question = request.question.strip()
    if not question:
        return BankingChatResponse(
            answer="I'm sorry, I didn't receive a question. Please type something and try again.",
            sources=[], model_used="policy", rag_context_found=False,
            question="", detected_language="English", query_type="general",
        )

    user_label = current_user.username if current_user else "guest"
    logger.info(f"[{user_label}] Query: '{question[:80]}'")

    # ── Step 1: Language detection ─────────────────────────────────────────────
    detected_language, english_query = _detect_and_translate(question, llm)
    is_english = detected_language.lower() == "english"
    language_instruction = (
        f"\n\nIMPORTANT: Respond in {detected_language}, not English." if not is_english else ""
    )

    # ── Step 2: Route query type ───────────────────────────────────────────────
    personal  = is_personal_query(english_query)
    financial = is_financial_query(english_query)
    # For a logged-in customer, treat ANY financial query as personal so real data is used
    needs_customer_data = personal or (financial and current_user is not None)

    customer_context = ""
    rag_context_text = ""
    sources = []
    rag_context_found = False
    query_type = "general"

    if personal and current_user is None:
        # Guest using personal pronouns (my/me) → immediate login deflection
        # NOTE: generic financial keywords (loan, account, card) alone do NOT deflect guests —
        # those are general FAQ questions answerable via RAG without account data.
        logger.info(f"[guest] Personal query deflected: '{question[:60]}'")
        return BankingChatResponse(
            answer=LOGIN_REQUIRED_RESPONSE,
            sources=[],
            model_used="policy",
            rag_context_found=False,
            question=question,
            detected_language=detected_language,
            query_type="personal_guest",
        )

    if needs_customer_data and current_user and current_user.is_customer():
        query_type = "personal"
        customer_context = _build_customer_context(current_user.user_id)
        logger.info(f"[{current_user.username}] Customer context injected (personal={personal}, financial={financial})")
        # Also enrich with RAG
        if rag.is_ready():
            try:
                rag_context_text, raw_sources = rag.get_context_and_sources(english_query, n_results=3)
                rag_context_found = bool(rag_context_text)
                sources = [SourceCitation(**s) for s in raw_sources]
            except Exception:
                pass

    elif rag.is_ready():
        try:
            rag_context_text, raw_sources = rag.get_context_and_sources(english_query, n_results=5)
            rag_context_found = bool(rag_context_text)
            sources = [SourceCitation(**s) for s in raw_sources]
        except Exception as e:
            logger.warning(f"RAG failed: {e}")

    # ── Step 3: Build prompt ───────────────────────────────────────────────────
    user_display = current_user.full_name if current_user else "Guest"
    user_role    = current_user.role      if current_user else "guest"

    prompt_parts = [
        f"Customer Question (original): {question}",
        f"Customer Question (English): {english_query}" if not is_english else "",
        f"\nAssistant User: {user_display} (Role: {user_role})",
    ]

    if customer_context:
        prompt_parts.append(f"\n## Verified Customer Data from Secure Database\n{customer_context}")
        prompt_parts.append(
            "\n GROUNDING RULES FOR CUSTOMER DATA:\n"
            "- Use ONLY the transaction list above. If the list has fewer transactions than requested, "
            "say exactly how many are available and list ALL of them. NEVER invent, guess, or fabricate "
            "transactions, amounts, dates, or references.\n"
            "- Format amounts with the currency shown in each transaction (e.g. USD, INR).\n"
            "- Answer from the exact data provided above."
        )

    if rag_context_text:
        prompt_parts.append(f"\n## General Banking Knowledge Base\n{rag_context_text}")

    if not customer_context and not rag_context_text:
        prompt_parts.append("\nNo specific context retrieved. Provide general guidance and suggest contacting support.")

    prompt_parts.append(language_instruction)
    user_prompt = "\n".join(p for p in prompt_parts if p)

    # ── Step 4: LLM call ───────────────────────────────────────────────────────
    history = [{"role": t.role, "content": t.content} for t in (request.conversation_history or [])]
    try:
        answer, model_used = llm.chat_with_history(SYSTEM_PROMPT, history, user_prompt)
    except Exception as e:
        if _is_content_blocked(e) and (rag_context_text or customer_context):
            # The RAG / customer context triggered a content-safety filter.
            # Retry with a clean bare prompt so the user's innocent question still gets answered.
            logger.warning(
                "Content blocked — RAG/customer context contains flagged keywords. "
                "Retrying with bare question prompt."
            )
            bare_parts = [
                f"Customer Question: {question}",
                language_instruction,
            ]
            bare_prompt = "\n".join(p for p in bare_parts if p)
            try:
                answer, model_used = llm.chat_with_history(SYSTEM_PROMPT, history, bare_prompt)
                # Clear sources since we couldn't use the RAG context
                sources = []
                rag_context_found = False
            except Exception as inner_e:
                logger.error(f"LLM failed even on bare prompt: {inner_e}")
                answer = "I apologize, I'm temporarily unable to process your request. Please try again in a moment or call 1800-XXX-XXXX for assistance."
                model_used = "error"
        else:
            logger.error(f"LLM failed: {e}")
            answer = "I apologize, I'm temporarily unable to process your request. Please try again in a moment or call 1800-XXX-XXXX for assistance."
            model_used = "error"

    if not answer or not answer.strip():
        answer = "I apologize, I was unable to generate a response. Please contact our support team."
        model_used = "fallback"

    logger.info(f"Response: {model_used}, {query_type}, lang={detected_language}, chars={len(answer)}")

    return BankingChatResponse(
        answer=answer,
        sources=sources,
        model_used=model_used,
        rag_context_found=rag_context_found,
        question=question,
        detected_language=detected_language,
        query_type=query_type,
    )


# ── File Upload Endpoint ───────────────────────────────────────────────────────

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_PDF_TYPE    = "application/pdf"
MAX_FILE_MB         = 10

FILE_SYSTEM_PROMPT = """You are a secure AI Banking Assistant for The World Bank.
A customer has shared a file (image or document) and has a question about it.

STRICT RULES:
1. Only analyse this file in the context of banking / financial services.
2. If the file appears to be a bank communication, verify its authenticity based on standard World Bank formats.
3. Never fabricate financial data not visible in the file.
4. Be professional, concise and honest. If you cannot read the file clearly, say so.
5. Respond in the EXACT SAME LANGUAGE as the customer's question."""


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using PyMuPDF. Returns up to 8000 chars."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = []
        for page in doc:
            pages.append(page.get_text())
        text = "\n".join(pages).strip()
        return text[:8000]  # keep within context limits
    except Exception as e:
        logger.warning(f"PDF text extraction failed: {e}")
        return ""


@router.post("/upload", response_model=BankingChatResponse)
async def banking_assistant_upload(
    file: UploadFile = File(...),
    question: str = Form("Please analyse this file."),
    conversation_history: str = Form("[]"),
    current_user: Optional[CurrentUser] = Depends(get_optional_user),
    llm: LLMService = Depends(get_llm_service),
):
    """
    POST /process/upload  – multipart endpoint for image / PDF analysis.
    Requires authentication (guests are redirected with a polite message).
    """
    # ── Auth gate ──────────────────────────────────────────────────────────────
    if current_user is None:
        return BankingChatResponse(
            answer=LOGIN_REQUIRED_RESPONSE,
            sources=[], model_used="policy", rag_context_found=False,
            question=question, detected_language="English",
            query_type="personal_guest",
        )

    # ── Validate file ──────────────────────────────────────────────────────────
    content_type = (file.content_type or "").lower()
    is_image = content_type in ALLOWED_IMAGE_TYPES
    is_pdf   = content_type == ALLOWED_PDF_TYPE

    if not is_image and not is_pdf:
        return BankingChatResponse(
            answer="I'm sorry, only image files (JPEG, PNG, WEBP) and PDF documents are supported. Please upload a valid file.",
            sources=[], model_used="policy", rag_context_found=False,
            question=question, detected_language="English", query_type="general",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_MB * 1024 * 1024:
        return BankingChatResponse(
            answer=f"The file is too large. Please upload a file smaller than {MAX_FILE_MB} MB.",
            sources=[], model_used="policy", rag_context_found=False,
            question=question, detected_language="English", query_type="general",
        )

    # ── Parse conversation history ─────────────────────────────────────────────
    try:
        history_raw = json.loads(conversation_history or "[]")
        history = [{"role": t["role"], "content": t["content"]} for t in history_raw if "role" in t]
    except Exception:
        history = []

    user_label = current_user.username if current_user else "guest"
    logger.info(f"[{user_label}] File upload: {file.filename} ({content_type}), Q: '{question[:60]}'")

    # ── IMAGE path → vision model ──────────────────────────────────────────────
    if is_image:
        image_b64 = base64.b64encode(file_bytes).decode()
        vision_prompt = (
            f"The customer uploaded an image ({file.filename or 'screenshot'}) "
            f"and asks: {question}\n\n"
            "Please analyse the image carefully and provide a helpful, accurate response."
        )
        answer, model_used = llm.chat_with_image(
            system_prompt=FILE_SYSTEM_PROMPT,
            history=history,
            user_text=vision_prompt,
            image_b64=image_b64,
            image_mime=content_type,
        )
        return BankingChatResponse(
            answer=answer or "I'm sorry, I could not analyse the image. Please try again.",
            sources=[], model_used=model_used, rag_context_found=False,
            question=question, detected_language="English", query_type="file_image",
        )

    # ── PDF path → text extraction → text LLM ─────────────────────────────────
    pdf_text = _extract_pdf_text(file_bytes)
    if not pdf_text:
        return BankingChatResponse(
            answer="I was unable to extract text from this PDF. It may be scanned/image-only. Please try uploading an image (screenshot) of the document instead.",
            sources=[], model_used="policy", rag_context_found=False,
            question=question, detected_language="English", query_type="file_pdf",
        )

    pdf_prompt = (
        f"The customer uploaded a PDF document titled '{file.filename or 'document'}'.\n\n"
        f"## Document Content (extracted text)\n{pdf_text}\n\n"
        f"## Customer Question\n{question}"
    )

    try:
        answer, model_used = llm.chat_with_history(FILE_SYSTEM_PROMPT, history, pdf_prompt)
    except Exception as e:
        if _is_content_blocked(e):
            answer = "I'm sorry, the document contains content that cannot be processed by the AI safety filters. Please contact support for assistance."
            model_used = "error"
        else:
            logger.error(f"PDF LLM failed: {e}")
            answer = "I apologize, I'm temporarily unable to process this document. Please try again in a moment."
            model_used = "error"

    return BankingChatResponse(
        answer=answer or "I'm sorry, I could not analyse this document. Please try again.",
        sources=[], model_used=model_used, rag_context_found=False,
        question=question, detected_language="English", query_type="file_pdf",
    )
