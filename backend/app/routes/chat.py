from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from app.services.llm_service import LLMService, get_llm_service

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    input: str = Field(..., min_length=1, description="The chat input prompt")


class ChatResponse(BaseModel):
    response: str


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    llm: LLMService = Depends(get_llm_service)
):
    """Accepts user input, calls the standard chat MAAS model, and returns a response."""
    logger.info(f"Received chat request: {request.input[:50]}...")
    try:
        response_text = llm.call_chat_model(request.input)
        return ChatResponse(response=response_text)
    except Exception as e:
        logger.error(f"Error in chat_endpoint: {e}")
        return ChatResponse(response="I apologize, I'm temporarily unable to process your request. Please try again in a moment.")


# ── Translation endpoint ───────────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000, description="Text to translate")
    target_language: str = Field(..., min_length=2, max_length=60, description="Target language name, e.g. 'Hindi', 'French'")


class TranslateResponse(BaseModel):
    translated_text: str
    target_language: str


@router.post("/translate", response_model=TranslateResponse)
async def translate_endpoint(
    request: TranslateRequest,
    llm: LLMService = Depends(get_llm_service)
):
    """Translates the given text into the specified target language using the LLM."""
    logger.info(f"Translate request: {len(request.text)} chars → {request.target_language}")
    try:
        msgs = [
            SystemMessage(content=(
                f"You are a professional translator. Translate the following text to {request.target_language}. "
                "Return ONLY the translated text — no explanations, no prefixes, no markdown. "
                "Preserve the original formatting (bullet points, tables, line breaks, etc.)."
            )),
            HumanMessage(content=request.text),
        ]
        translated, _ = llm.fallback_chain_call(msgs)
        return TranslateResponse(
            translated_text=translated.strip(),
            target_language=request.target_language,
        )
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return TranslateResponse(
            translated_text=request.text,   # fallback: return original
            target_language=request.target_language,
        )
