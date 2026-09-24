import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("app.services.evaluation.dataset")


class GoldenQueryItem(BaseModel):
    """Schema for a single golden evaluation query benchmark item.
    Supports both answerable policy queries (with expected chunks) and
    negative/unanswerable queries (testing zero-retrieval refusal behavior).
    """
    id: str = Field(..., description="Unique alphanumeric identifier for test item (e.g. hr_001)")
    query: str = Field(..., description="User question or inquiry")
    expected_chunk_ids: List[str] = Field(
        default_factory=list,
        description="List of expected chunk IDs or chunk reference identifiers that contain the answer"
    )
    reference_answer: Optional[str] = Field(
        default=None,
        description="Ground-truth reference answer used for relevance/accuracy comparison"
    )
    category: str = Field(
        default="general",
        description="Semantic category (e.g. leave_policy, benefits, conduct, out_of_scope)"
    )
    answerable: bool = Field(
        default=True,
        description="Whether this query has an answer in the company knowledge base"
    )

    @field_validator("id")
    @classmethod
    def validate_id_not_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Evaluation item ID cannot be empty.")
        return s

    @field_validator("query")
    @classmethod
    def validate_query_not_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Evaluation query cannot be empty.")
        return s


class DatasetValidator:
    """Validator utility for evaluation datasets."""

    @staticmethod
    def validate_items(items: List[Dict[str, Any]]) -> List[GoldenQueryItem]:
        """Validates a list of dictionaries into GoldenQueryItem instances."""
        if not items:
            raise ValueError("Dataset cannot be empty.")

        validated: List[GoldenQueryItem] = []
        seen_ids = set()

        for idx, raw in enumerate(items):
            try:
                item = GoldenQueryItem(**raw)
            except Exception as e:
                raise ValueError(f"Item #{idx} failed schema validation: {e}") from e

            if item.id in seen_ids:
                raise ValueError(f"Duplicate query ID found in dataset: '{item.id}' at index {idx}")
            seen_ids.add(item.id)

            # Invariant: If answerable is True, expected_chunk_ids should ideally be specified
            if item.answerable and not item.expected_chunk_ids:
                logger.warning(f"Item '{item.id}' is marked answerable=True but has empty expected_chunk_ids.")

            validated.append(item)

        return validated

    @staticmethod
    def load_jsonl(file_path: Path | str) -> List[GoldenQueryItem]:
        """Loads and validates a JSONL file into a list of GoldenQueryItems."""
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Golden dataset file not found at: {p.resolve()}")

        raw_items: List[Dict[str, Any]] = []
        with open(p, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                clean = line.strip()
                if not clean or clean.startswith("#"):
                    continue
                try:
                    data = json.loads(clean)
                    raw_items.append(data)
                except json.JSONDecodeError as jde:
                    raise ValueError(f"Invalid JSON at line {line_no} in {p.name}: {jde}") from jde

        return DatasetValidator.validate_items(raw_items)
