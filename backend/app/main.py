from contextlib import asynccontextmanager
import logging
from typing import Any, Dict
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import async_engine
from app.middleware.error_handler import register_exception_handlers
from app.middleware.logging import StructuredLoggingMiddleware

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup structured logging
    setup_logging(settings.LOG_LEVEL)
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    
    # Validate critical platform invariants
    from app.services.invariants import validate_embedding_dimension_invariant
    validate_embedding_dimension_invariant()
    
    # Initialize database tables automatically for all database backends
    import app.models  # noqa: F401 - register all models with Base.metadata
    from app.models.base import Base

    def _sync_sqlite_schema(sync_conn):
        for table_name, table in Base.metadata.tables.items():
            res = sync_conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
            if not res:
                continue
            existing_cols = {row[1] for row in res}
            for col in table.columns:
                if col.name not in existing_cols:
                    col_type = col.type.compile(sync_conn.dialect)
                    sync_conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"))

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "sqlite" in settings.DATABASE_URL:
            await conn.run_sync(_sync_sqlite_schema)
    logger.info("Database schema verified and synchronized.")

    # Automatically seed the Demo Account & Knowledge Bases on startup
    try:
        from app.db.session import async_session_factory
        from app.services.seed_service import SeedService
        async with async_session_factory() as seed_db:
            await SeedService.seed_demo_account(seed_db)
    except Exception as se:
        logger.warning(f"Could not complete automatic demo seeding on startup: {se}")
    
    # Recover any stale jobs from previous server crash
    try:
        from app.workers.ingestion_worker import IngestionWorker
        startup_worker = IngestionWorker()
        recovered = await startup_worker.recover_stale_jobs(
            timeout_seconds=settings.INGESTION_JOB_TIMEOUT_SECONDS
        )
        if recovered:
            logger.info(f"IngestionWorker: Recovered {recovered} stale jobs on application startup.")
    except Exception as e:
        logger.warning(f"Could not run startup stale job recovery: {e}")

    yield
    # Graceful shutdown
    logger.info("Shutting down database engine connections...")
    await async_engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Exception handlers
register_exception_handlers(app)

# Structured request logging middleware
app.add_middleware(StructuredLoggingMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origin_regex=r"^https?:\/\/.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health() -> Dict[str, str]:
    """Liveness probe to confirm backend is running."""
    return {"status": "ok"}


@app.get("/ready", tags=["Health"])
async def readiness() -> JSONResponse:
    """Readiness probe verifying operational status and database connection."""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ready", "database": "connected"},
        )
    except Exception as exc:
        logger.error(f"Readiness check failed: {exc}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "error": "Database unavailable"},
        )


# Register API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)
