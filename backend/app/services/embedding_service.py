import os
from langchain_openai import OpenAIEmbeddings
import httpx
from dotenv import load_dotenv

load_dotenv()

MAAS_API_KEY = os.getenv("MAAS_API_KEY", "YOUR_KEY_HERE")
MAAS_BASE_URL = "https://genailab.tcs.in"

# Disable SSL verification for MAAS pattern
client = httpx.Client(verify=False)

# Initialize Embedding Model
embedding_model = OpenAIEmbeddings(
    base_url=MAAS_BASE_URL,
    model="azure/genailab-maas-text-embedding-3-large",
    api_key=MAAS_API_KEY,
    http_client=client
)

def get_embeddings(text: str) -> list[float]:
    """
    Gets the vector embedding for the given text.
    """
    try:
        # We need to wrap text in a list depending on LangChain version, or embed_query
        return embedding_model.embed_query(text)
    except Exception as e:
        print(f"Error calling embedding model: {e}")
        return []
