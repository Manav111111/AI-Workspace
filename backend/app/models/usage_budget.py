import datetime
from decimal import Decimal
from typing import Optional
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class ModelPricingVersion(BaseModel):
    """Centralized, versioned model pricing table.
    Enables deterministic, reproducible cost calculations without modifying historical usage records.
    Prices expressed per 1,000,000 tokens (industry standard) using decimal-safe arithmetic.
    """
    __tablename__ = "model_pricing_versions"

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # "gemini", "openai", "mock"
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )  # "gemini-3.6-flash", "gpt-4o", etc.
    version_tag: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="2026-09-01",
        index=True,
    )
    input_price_per_million: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        default=Decimal("0.075000"),  # e.g., $0.075 / 1M for Gemini Flash
        nullable=False,
    )
    output_price_per_million: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        default=Decimal("0.300000"),  # e.g., $0.30 / 1M
        nullable=False,
    )
    cached_input_price_per_million: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        default=Decimal("0.018750"),  # e.g., 75% discount
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="USD",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
    )
    effective_from: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )


class UsageLedgerEntry(BaseModel):
    """Authoritative financial and token consumption ledger entry.
    Tracks each provider invocation with decimal precision and clear distinction
    between authoritative provider-reported usage and tokenizer estimates.
    """
    __tablename__ = "usage_ledger_entries"

    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ai_employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("ai_employees.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        nullable=True,
        index=True,
    )
    trace_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    operation_type: Mapped[str] = mapped_column(
        String(50),
        default="LLM_GENERATION",
        nullable=False,
        index=True,
    )  # "LLM_GENERATION", "EMBEDDING", "RERANKING", "VOICE_STT", "VOICE_TTS", "LLM_JUDGE"

    # Token counts
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    audio_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Cost calculation (decimal-safe)
    estimated_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        default=Decimal("0.000000"),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    cost_status: Mapped[str] = mapped_column(
        String(30),
        default="FINAL",
        nullable=False,
        index=True,
    )  # "FINAL", "ESTIMATED", "UNAVAILABLE"
    usage_source: Mapped[str] = mapped_column(
        String(40),
        default="PROVIDER_REPORTED",
        nullable=False,
        index=True,
    )  # "PROVIDER_REPORTED", "TOKENIZER_ESTIMATED", "PROVIDER_ESTIMATED", "UNKNOWN"
    pricing_version_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # Relationships
    company = relationship("Company")
    ai_employee = relationship("AIEmployee")


class UsageBudget(BaseModel):
    """Company-level or AI Employee-specific spend limit and governance policy.
    Supports soft warning thresholds and hard blocking enforcement.
    """
    __tablename__ = "usage_budgets"

    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ai_employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("ai_employees.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    budget_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Monthly Budget",
    )
    limit_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )  # Limit in currency units (e.g., $50.0000)
    currency: Mapped[str] = mapped_column(
        String(10),
        default="USD",
        nullable=False,
    )
    period_type: Mapped[str] = mapped_column(
        String(30),
        default="MONTHLY",
        nullable=False,
        index=True,
    )  # "MONTHLY", "WEEKLY", "DAILY"
    soft_limit_percent: Mapped[float] = mapped_column(
        Float,
        default=80.0,
        nullable=False,
    )  # Threshold (e.g., 80.0%) to trigger warning events
    hard_limit_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )  # If true, block requests when 100% is reached
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # Relationships
    company = relationship("Company")
    ai_employee = relationship("AIEmployee")
