"""
RAG Service – Banking FAQ Retrieval
-------------------------------------
Queries ChromaDB for relevant FAQ chunks and formats context for LLM.
"""

import logging
import httpx
import chromadb
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from app.config import settings

logger = logging.getLogger(__name__)

# Resolve an absolute path for ChromaDB — backend/app/services -> parents[2] = backend/
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_CHROMA_PATH = str(_BACKEND_DIR / "chroma_db") if settings.chroma_db_path == "./chroma_db" else settings.chroma_db_path


class RAGService:
    def __init__(self):
        self.http_client = httpx.Client(verify=False)
        self._init_embedding_model()
        self._init_chroma()

    def _init_embedding_model(self):
        try:
            self.embedding_model = OpenAIEmbeddings(
                base_url=settings.maas_base_url,
                model=settings.embedding_model_name,
                api_key=settings.maas_api_key,
                http_client=self.http_client,
            )
            logger.info("RAG embedding model initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            self.embedding_model = None

    def _init_chroma(self):
        try:
            logger.info(f"Loading ChromaDB from: {_CHROMA_PATH}")
            self.chroma_client = chromadb.PersistentClient(path=_CHROMA_PATH)
            self.collection = self.chroma_client.get_collection(settings.chroma_collection)
            count = self.collection.count()
            logger.info(f"ChromaDB loaded: '{settings.chroma_collection}' with {count} documents.")
        except Exception as e:
            logger.warning(f"ChromaDB not ready (run ingest.py first): {e}")
            self.collection = None


    def is_ready(self) -> bool:
        return self.collection is not None and self.embedding_model is not None

    def query(self, question: str, n_results: int = 5) -> dict:
        """
        Retrieve top-k relevant chunks from ChromaDB.
        Returns dict with 'documents', 'metadatas', 'distances'.
        """
        if not self.is_ready():
            return {"documents": [], "metadatas": [], "distances": []}

        try:
            query_embedding = self.embedding_model.embed_query(question)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, self.collection.count()),
                include=["documents", "metadatas", "distances"],
            )
            return {
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "distances": results["distances"][0] if results["distances"] else [],
            }
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {"documents": [], "metadatas": [], "distances": []}

    def get_context_and_sources(self, question: str, n_results: int = 5, distance_threshold: float = 1.2):
        """
        Returns:
            context_text (str): Formatted context for LLM prompt
            sources (list[dict]): Citation list for frontend display
        """
        results = self.query(question, n_results)

        context_parts = []
        sources = []

        for doc, meta, dist in zip(
            results["documents"], results["metadatas"], results["distances"]
        ):
            if dist > distance_threshold:
                continue  # Skip low-relevance chunks

            topic = meta.get("topic", "general").replace("_", " ").title()
            source = meta.get("source", "Banking Policy")
            context_parts.append(f"[Source: {source} | Topic: {topic}]\n{doc}")

            # Deduplicate sources by source name
            if not any(s["source"] == source for s in sources):
                sources.append({
                    "source": source,
                    "topic": topic,
                    "excerpt": doc[:200] + "..." if len(doc) > 200 else doc,
                    "relevance_score": round(1 - dist, 3),
                })

        context_text = "\n\n---\n\n".join(context_parts) if context_parts else ""
        return context_text, sources


# Global singleton
rag_service = RAGService()


def get_rag_service() -> RAGService:
    return rag_service
