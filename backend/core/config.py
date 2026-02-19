from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./rag_database.db"
    # JWT
    secret_key: str = "9ae66d1ffe7c2880c7dae5a157b26943d2dd8facbaa79003fe15d9f98ea90466"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    # OpenAI
    openai_api_key: str = "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"
    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Application
    upload_dir: str = "./uploads"
    max_file_size: int = 10485760
    chunk_size: int = 400
    chunk_overlap: int = 50
    top_k: int = 3
    similarity_threshold: float = 0.7
    # Additional fields to match .env
    vector_store: str = "faiss"
    llm_model: str = "gpt-3.5-turbo"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 500
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    log_level: str = "INFO"
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    session_timeout: int = 60
    environment: str = "development"
    debug: bool = True

    class Config:
        env_file = ".env"
        extra = "allow"

@lru_cache()
def get_settings():
    return Settings()