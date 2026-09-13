from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid
from app.core.config import settings
from app.services.cleaning import TextCleaner
from app.services.parsers.base import ParsedSection


@dataclass
class RawChunk:
    chunk_index: int
    content: str
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChunkingService:
    """Splits structured parsed document sections into semantic chunks preserving metadata."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def _estimate_tokens(self, text: str) -> int:
        # Approximate 1 token ~= 4 characters / 0.75 words
        return max(1, len(text.split()))

    def chunk_sections(
        self,
        sections: List[ParsedSection],
        company_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> List[RawChunk]:
        chunks: List[RawChunk] = []
        current_chunk_idx = 0

        for section in sections:
            cleaned_text = TextCleaner.clean(section.content)
            if not cleaned_text:
                continue

            # If section fits within chunk size, keep it intact
            if len(cleaned_text) <= self.chunk_size:
                meta = dict(section.metadata)
                meta.update({
                    "company_id": str(company_id),
                    "knowledge_base_id": str(knowledge_base_id),
                    "document_id": str(document_id),
                })
                chunks.append(
                    RawChunk(
                        chunk_index=current_chunk_idx,
                        content=cleaned_text,
                        token_count=self._estimate_tokens(cleaned_text),
                        metadata=meta,
                    )
                )
                current_chunk_idx += 1
                continue

            # Otherwise split by paragraphs or sentences
            paragraphs = [p.strip() for p in cleaned_text.split("\n\n") if p.strip()]
            buffer = ""
            for p in paragraphs:
                if buffer and len(buffer) + len(p) + 2 > self.chunk_size:
                    meta = dict(section.metadata)
                    meta.update({
                        "company_id": str(company_id),
                        "knowledge_base_id": str(knowledge_base_id),
                        "document_id": str(document_id),
                    })
                    chunks.append(
                        RawChunk(
                            chunk_index=current_chunk_idx,
                            content=buffer.strip(),
                            token_count=self._estimate_tokens(buffer),
                            metadata=meta,
                        )
                    )
                    current_chunk_idx += 1
                    # Keep overlap from buffer tail
                    overlap_chars = buffer[-self.chunk_overlap :] if len(buffer) > self.chunk_overlap else ""
                    buffer = (overlap_chars + " " + p).strip()
                else:
                    buffer = f"{buffer}\n\n{p}".strip() if buffer else p

            if buffer.strip():
                meta = dict(section.metadata)
                meta.update({
                    "company_id": str(company_id),
                    "knowledge_base_id": str(knowledge_base_id),
                    "document_id": str(document_id),
                })
                chunks.append(
                    RawChunk(
                        chunk_index=current_chunk_idx,
                        content=buffer.strip(),
                        token_count=self._estimate_tokens(buffer),
                        metadata=meta,
                    )
                )
                current_chunk_idx += 1

        return chunks
