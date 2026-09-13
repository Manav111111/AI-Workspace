from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "AI Employee Platform"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str = "dev-secret-key-super-secure-change-in-prod-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_employee_platform"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/ai_employee_platform"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Document Ingestion & Storage
    MAX_UPLOAD_SIZE_MB: int = 25
    STORAGE_ROOT: str = "./uploads"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # Embeddings & Vector Search (Qdrant)
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Union[str, None] = None
    QDRANT_COLLECTION_PREFIX: str = "kb_"

    # RAG & Retrieval
    RAG_TOP_K: int = 5
    RAG_SCORE_THRESHOLD: float = 0.05
    RAG_MAX_CONTEXT_CHUNKS: int = 5
    CONVERSATION_HISTORY_MESSAGES: int = 10

    # LLM Configuration
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: Union[str, None] = None
    OPENAI_API_BASE: Union[str, None] = None
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1000
    LLM_TIMEOUT_SECONDS: int = 60

    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
