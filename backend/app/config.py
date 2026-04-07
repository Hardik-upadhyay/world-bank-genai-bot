from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    maas_api_key: str = "DEFAULT_KEY"
    maas_base_url: str = "https://genailab.tcs.in"

    # Primary chat model
    chat_model_name: str = "azure_ai/genailab-maas-DeepSeek-V3-0324"
    reasoning_model_name: str = "azure_ai/genailab-maas-DeepSeek-R1"
    embedding_model_name: str = "azure/genailab-maas-text-embedding-3-large"

    # Fallback chain models
    fallback_model_1: str = "azure/genailab-maas-gpt-4o"
    fallback_model_2: str = "azure/genailab-maas-gpt-4o-mini"
    fallback_model_3: str = "azure/genailab-maas-gpt-35-turbo"

    # ChromaDB
    chroma_db_path: str = "./chroma_db"
    chroma_collection: str = "banking_faq"

    # JWT Auth
    jwt_secret_key: str = "world-bank-super-secret-jwt-key-2025"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 hours

    # SQLite
    sqlite_db_path: str = "./world_bank.db"

    cors_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
