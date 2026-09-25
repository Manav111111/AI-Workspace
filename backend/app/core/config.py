from typing import List, Union
from pathlib import Path
from dotenv import load_dotenv
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load backend/.env with override=True so workspace configuration takes precedence over stale OS environment variables
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=True)
else:
    load_dotenv(override=True)


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
    CHUNKING_PROVIDER: str = "local"  # "local" | "gemini"

    # Embeddings & Vector Search (Qdrant)
    EMBEDDING_PROVIDER: str = "gemini"  # "gemini" | "cpu" | "mock"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 20
    EMBEDDING_TIMEOUT_SECONDS: int = 30
    EMBEDDING_MAX_RETRIES: int = 3
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Union[str, None] = None
    QDRANT_COLLECTION_PREFIX: str = "kb_"

    # RAG & Retrieval
    RAG_TOP_K: int = 5
    RAG_SCORE_THRESHOLD: float = 0.05
    RAG_MAX_CONTEXT_CHUNKS: int = 5
    CONVERSATION_HISTORY_MESSAGES: int = 10

    # Phase 9: Hybrid Retrieval & Reranking
    RETRIEVAL_MODE: str = "dense"  # "dense" | "sparse" | "hybrid"
    RETRIEVAL_DENSE_TOP_K: int = 10
    RETRIEVAL_SPARSE_TOP_K: int = 10
    RETRIEVAL_CANDIDATE_K: int = 20
    RETRIEVAL_FINAL_TOP_K: int = 5
    RETRIEVAL_RRF_K: int = 60
    RERANKER_ENABLED: bool = False
    RERANKER_PROVIDER: str = "noop"  # "noop" | "cross_encoder" | "heuristic"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_TOP_K: int = 5
    RERANKER_TIMEOUT_MS: int = 2000

    # Phase 10: Async Ingestion & Distributed Rate Limiting
    INGESTION_MAX_CONCURRENCY: int = 3
    INGESTION_MAX_RETRIES: int = 3
    INGESTION_JOB_TIMEOUT_SECONDS: int = 300
    INGESTION_RETRY_BACKOFF_SECONDS: int = 2
    MAX_QUEUED_INGESTION_JOBS_PER_COMPANY: int = 20
    MAX_CONCURRENT_INGESTION_PER_COMPANY: int = 3
    RATE_LIMIT_BACKEND: str = "redis"  # "redis" | "memory"
    RATE_LIMIT_REDIS_TIMEOUT_SECONDS: float = 0.5
    RATE_LIMIT_PUBLIC_CONFIG_PER_MINUTE: int = 60
    RATE_LIMIT_PUBLIC_SESSION_PER_MINUTE: int = 20
    RATE_LIMIT_PUBLIC_MESSAGE_PER_MINUTE: int = 30
    RATE_LIMIT_EVALUATION_RUN_PER_HOUR: int = 5
    RATE_LIMIT_DOCUMENT_UPLOAD_PER_MINUTE: int = 10


    # LLM Configuration
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-3.6-flash"
    OPENAI_API_KEY: Union[str, None] = None
    OPENAI_API_BASE: Union[str, None] = None
    GEMINI_API_KEY: Union[str, None] = None
    GOOGLE_API_KEY: Union[str, None] = None
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1000
    LLM_TIMEOUT_SECONDS: int = 60

    # Voice AI Configuration (Phase 5)
    VOICE_STT_PROVIDER: str = "mock"  # "mock" | "openai" | "deepgram"
    VOICE_TTS_PROVIDER: str = "mock"  # "mock" | "openai" | "elevenlabs"
    DEEPGRAM_API_KEY: Union[str, None] = None
    ELEVENLABS_API_KEY: Union[str, None] = None
    VOICE_MAX_SESSION_DURATION_SECONDS: int = 1800  # 30 mins
    VOICE_MAX_AUDIO_CHUNK_SIZE_BYTES: int = 1024 * 1024  # 1 MB
    VOICE_MAX_CONCURRENT_SESSIONS_PER_TENANT: int = 10
    VOICE_RATE_LIMIT_PER_MINUTE: int = 30
    VOICE_TTS_BUFFER_MIN_CHARS: int = 35

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
        env_file=str(_env_path),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
