from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    openai_api_key: str = ""
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    database_url: str = "postgresql://rag:rag@localhost:5432/rag"

    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_k: int = 20   # candidats récupérés dans pgvector
    final_k: int = 5        # passages gardés après reranking
    rerank_enabled: bool = True

    cors_origins: str = "http://localhost:3000"
    max_upload_mb: int = 50


settings = Settings()
