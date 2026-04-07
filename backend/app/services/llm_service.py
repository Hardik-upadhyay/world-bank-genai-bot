import logging
import base64
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        # Disable SSL verification for MAAS API pattern as required
        self.client = httpx.Client(verify=False)

        try:
            self.chat_model = ChatOpenAI(
                base_url=settings.maas_base_url,
                model=settings.chat_model_name,
                api_key=settings.maas_api_key,
                http_client=self.client,
                max_retries=2,
            )

            self.reasoning_model = ChatOpenAI(
                base_url=settings.maas_base_url,
                model=settings.reasoning_model_name,
                api_key=settings.maas_api_key,
                http_client=self.client,
                max_retries=2,
            )

            # Fallback chain: GPT-4o → GPT-4o-mini → GPT-3.5
            self.fallback_models = [
                (
                    "GPT-4o",
                    ChatOpenAI(
                        base_url=settings.maas_base_url,
                        model=settings.fallback_model_1,
                        api_key=settings.maas_api_key,
                        http_client=self.client,
                        max_retries=1,
                    ),
                ),
                (
                    "GPT-4o-mini",
                    ChatOpenAI(
                        base_url=settings.maas_base_url,
                        model=settings.fallback_model_2,
                        api_key=settings.maas_api_key,
                        http_client=self.client,
                        max_retries=1,
                    ),
                ),
                (
                    "GPT-3.5",
                    ChatOpenAI(
                        base_url=settings.maas_base_url,
                        model=settings.fallback_model_3,
                        api_key=settings.maas_api_key,
                        http_client=self.client,
                        max_retries=1,
                    ),
                ),
            ]
        except Exception as e:
            logger.error(f"Failed to initialize LLM models: {e}")
            self.chat_model = None
            self.reasoning_model = None
            self.fallback_models = []

    def call_chat_model(self, prompt: str) -> str:
        if not self.chat_model:
            raise RuntimeError("Chat model is not properly initialized.")
        try:
            response = self.chat_model.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"Error calling chat model: {e}")
            raise RuntimeError(f"Failed to generate chat response: {e}")

    def call_reasoning_model(self, prompt: str) -> str:
        if not self.reasoning_model:
            raise RuntimeError("Reasoning model is not properly initialized.")
        try:
            response = self.reasoning_model.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"Error calling reasoning model: {e}")
            raise RuntimeError(f"Failed to generate reasoning: {e}")

    def fallback_chain_call(self, messages: list) -> tuple[str, str]:
        """
        Try GPT-4o -> GPT-4o-mini -> GPT-3.5 in order.
        Returns (response_text, model_label_used).
        """
        last_error = None
        for model_label, model in self.fallback_models:
            try:
                logger.info(f"Trying fallback model: {model_label}")
                response = model.invoke(messages)
                logger.info(f"[OK] Got response from {model_label}")
                return response.content, model_label
            except Exception as e:
                logger.warning(f"[FAIL] {model_label} failed: {e}")
                last_error = e
                continue

        raise RuntimeError(f"All fallback models failed. Last error: {last_error}")

    def chat_with_history(self, system_prompt: str, history: list, user_message: str) -> tuple[str, str]:
        """
        Build a message list from history.
        Tries primary DeepSeek chat model first; falls back to GPT chain on failure.
        history: list of {"role": "user"|"assistant", "content": str}
        Returns (response_text, model_label).
        """
        messages = [SystemMessage(content=system_prompt)]
        for turn in history[-6:]:  # Keep last 6 turns (3 user + 3 assistant)
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            elif turn["role"] == "assistant":
                messages.append(AIMessage(content=turn["content"]))
        messages.append(HumanMessage(content=user_message))

        # --- Try primary model (DeepSeek-V3) first ---
        if self.chat_model:
            try:
                logger.info("Calling primary chat model (DeepSeek-V3)...")
                response = self.chat_model.invoke(messages)
                content = response.content
                if content and content.strip():
                    logger.info("[OK] Primary model responded successfully.")
                    return content, "DeepSeek-V3"
                logger.warning("Primary model returned empty response, trying fallback chain.")
            except Exception as e:
                logger.warning(f"Primary model failed ({e}), switching to fallback chain.")

        # --- Fallback chain: GPT-4o -> GPT-4o-mini -> GPT-3.5 ---
        return self.fallback_chain_call(messages)

    def chat_with_image(
        self,
        system_prompt: str,
        history: list,
        user_text: str,
        image_b64: str,
        image_mime: str = "image/jpeg",
    ) -> tuple[str, str]:
        """
        Send an image + text message to a vision-capable model (GPT-4o).
        Returns (response_text, model_label).
        """
        messages = [SystemMessage(content=system_prompt)]
        for turn in history[-4:]:  # fewer turns to save context for image
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            elif turn["role"] == "assistant":
                messages.append(AIMessage(content=turn["content"]))

        # Vision message: content is a list with text + image_url blocks
        vision_content = [
            {"type": "text", "text": user_text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image_mime};base64,{image_b64}"},
            },
        ]
        messages.append(HumanMessage(content=vision_content))

        # Try GPT-4o first (vision-capable); then fall back down the chain
        for model_label, model in self.fallback_models:
            try:
                logger.info(f"[vision] Trying {model_label}")
                response = model.invoke(messages)
                if response.content and response.content.strip():
                    logger.info(f"[vision] Got response from {model_label}")
                    return response.content, model_label
            except Exception as e:
                logger.warning(f"[vision] {model_label} failed: {e}")
                continue

        return (
            "I'm sorry, I was unable to analyse the image at this time. Please try again.",
            "error",
        )


# Global instance for FastAPI Depends
llm_service = LLMService()


def get_llm_service() -> LLMService:
    return llm_service
