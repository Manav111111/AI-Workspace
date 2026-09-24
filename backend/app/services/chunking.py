from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional
import uuid
from app.core.config import settings
from app.services.cleaning import TextCleaner
from app.services.parsers.base import ParsedSection

logger = logging.getLogger("app.services.chunking")


@dataclass
class RawChunk:
    chunk_index: int
    content: str
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChunkingService:
    """Splits structured parsed document sections into semantic chunks preserving metadata.
    Chunking remains decoupled from embeddings.
    Default: CHUNKING_PROVIDER='local'.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        provider: Optional[str] = None,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.provider = (provider or settings.CHUNKING_PROVIDER or "local").lower()

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

            base_meta = dict(section.metadata) if section.metadata else {}
            base_meta.update({
                "company_id": str(company_id),
                "knowledge_base_id": str(knowledge_base_id),
                "document_id": str(document_id),
            })
            if "source" not in base_meta and "source_file" in base_meta:
                base_meta["source"] = base_meta["source_file"]
            if "title" not in base_meta and "section_title" in base_meta:
                base_meta["title"] = base_meta["section_title"]

            # If section fits within chunk size, keep it intact
            if len(cleaned_text) <= self.chunk_size:
                meta = dict(base_meta)
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
                    meta = dict(base_meta)
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
                meta = dict(base_meta)
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
