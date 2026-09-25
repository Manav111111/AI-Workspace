from dataclasses import dataclass
import datetime
from decimal import Decimal
import logging
from typing import Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usage_budget import ModelPricingVersion

logger = logging.getLogger("app.services.billing.pricing")


@dataclass
class PricingRule:
    provider: str
    model: str
    input_price_per_million: Decimal
    output_price_per_million: Decimal
    cached_input_price_per_million: Decimal
    currency: str = "USD"
    version_tag: str = "2026-09-01"


# Default base pricing catalog (expressed in USD per 1,000,000 tokens)
DEFAULT_PRICING: Dict[Tuple[str, str], PricingRule] = {
    # Gemini models
    ("gemini", "gemini-3.6-flash"): PricingRule(
        provider="gemini",
        model="gemini-3.6-flash",
        input_price_per_million=Decimal("0.075000"),
        output_price_per_million=Decimal("0.300000"),
        cached_input_price_per_million=Decimal("0.018750"),
    ),
    ("gemini", "gemini-2.5-flash-lite"): PricingRule(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        input_price_per_million=Decimal("0.037500"),
        output_price_per_million=Decimal("0.150000"),
        cached_input_price_per_million=Decimal("0.009375"),
    ),
    ("gemini", "gemini-flash-latest"): PricingRule(
        provider="gemini",
        model="gemini-flash-latest",
        input_price_per_million=Decimal("0.075000"),
        output_price_per_million=Decimal("0.300000"),
        cached_input_price_per_million=Decimal("0.018750"),
    ),
    # OpenAI models
    ("openai", "gpt-4o"): PricingRule(
        provider="openai",
        model="gpt-4o",
        input_price_per_million=Decimal("2.500000"),
        output_price_per_million=Decimal("10.000000"),
        cached_input_price_per_million=Decimal("1.250000"),
    ),
    ("openai", "gpt-4o-mini"): PricingRule(
        provider="openai",
        model="gpt-4o-mini",
        input_price_per_million=Decimal("0.150000"),
        output_price_per_million=Decimal("0.600000"),
        cached_input_price_per_million=Decimal("0.075000"),
    ),
    # Mock offline testing model
    ("mock", "mock-model"): PricingRule(
        provider="mock",
        model="mock-model",
        input_price_per_million=Decimal("0.000000"),
        output_price_per_million=Decimal("0.000000"),
        cached_input_price_per_million=Decimal("0.000000"),
    ),
}


class ModelPricingRegistry:
    """Centralized registry for model pricing and deterministic cost calculations.
    Enforces decimal-safe financial calculations and guarantees that historical pricing
    changes do not retroactively alter previously recorded usage records.
    """

    @classmethod
    async def get_pricing(
        cls,
        session: Optional[AsyncSession],
        provider: str,
        model: str,
    ) -> Optional[PricingRule]:
        """Resolves pricing rule for a provider and model, checking the database first,
        then falling back to the standard base catalog.
        """
        clean_provider = provider.lower().strip()
        clean_model = model.lower().strip()

        if session:
            try:
                stmt = (
                    select(ModelPricingVersion)
                    .where(
                        ModelPricingVersion.provider == clean_provider,
                        ModelPricingVersion.model == clean_model,
                        ModelPricingVersion.is_active == True,
                    )
                    .order_by(ModelPricingVersion.effective_from.desc())
                    .limit(1)
                )
                res = await session.execute(stmt)
                db_rule = res.scalar_one_or_none()
                if db_rule:
                    return PricingRule(
                        provider=db_rule.provider,
                        model=db_rule.model,
                        input_price_per_million=Decimal(str(db_rule.input_price_per_million)),
                        output_price_per_million=Decimal(str(db_rule.output_price_per_million)),
                        cached_input_price_per_million=Decimal(str(db_rule.cached_input_price_per_million)),
                        currency=db_rule.currency,
                        version_tag=db_rule.version_tag,
                    )
            except Exception as e:
                logger.warning(f"Failed to query ModelPricingVersion from DB: {e}. Using default catalog.")

        # Check default catalog
        key = (clean_provider, clean_model)
        if key in DEFAULT_PRICING:
            return DEFAULT_PRICING[key]

        # Fuzzy match model prefix (e.g., "gemini-3.6-flash-preview" -> "gemini-3.6-flash")
        for (p, m), rule in DEFAULT_PRICING.items():
            if p == clean_provider and (clean_model.startswith(m) or m.startswith(clean_model)):
                return rule

        return None

    @classmethod
    def calculate_cost(
        cls,
        pricing: Optional[PricingRule],
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
    ) -> Tuple[Decimal, str, Optional[str]]:
        """Computes cost using decimal arithmetic.
        Returns: (estimated_cost, cost_status, version_tag)
        """
        if not pricing:
            return Decimal("0.000000"), "UNAVAILABLE", None

        # Price per token = price_per_million / 1,000,000
        ONE_MILLION = Decimal("1000000")

        # Non-cached input tokens
        effective_input = max(0, input_tokens - cached_tokens)
        input_cost = (Decimal(effective_input) * pricing.input_price_per_million) / ONE_MILLION
        output_cost = (Decimal(output_tokens) * pricing.output_price_per_million) / ONE_MILLION
        cached_cost = (Decimal(cached_tokens) * pricing.cached_input_price_per_million) / ONE_MILLION

        total_cost = (input_cost + output_cost + cached_cost).quantize(Decimal("0.000001"))
        return total_cost, "FINAL", pricing.version_tag
