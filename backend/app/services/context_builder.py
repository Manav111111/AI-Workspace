from typing import List, Optional
from app.core.config import settings
from app.services.retrieval import RetrievedChunk


class ContextBuilder:
    """Formats retrieved knowledge chunks into bounded, structured context for the LLM.
    Strictly isolates document content as reference material to prevent instruction injection.
    """

    def __init__(self, max_chunks: Optional[int] = None):
        self.max_chunks = max_chunks or settings.RAG_MAX_CONTEXT_CHUNKS

    def build_context(self, chunks: List[RetrievedChunk]) -> str:
        """Converts retrieved chunks into formatted reference blocks with source provenance."""
        if not chunks:
            return ""

        selected_chunks = chunks[: self.max_chunks]
        context_blocks = []

        for idx, chunk in enumerate(selected_chunks, start=1):
            source_name = chunk.source or "Document"
            page_info = f"Page: {chunk.page_number}" if chunk.page_number is not None else None
            header_info = f"Section: {chunk.header_path}" if chunk.header_path else None

            header_lines = [f"[SOURCE {idx}]", f"Document: {source_name}"]
            if page_info:
                header_lines.append(page_info)
            if header_info:
                header_lines.append(header_info)

            header_str = "\n".join(header_lines)
            block = f"{header_str}\nContent:\n{chunk.text.strip()}"
            context_blocks.append(block)

        return "\n\n---\n\n".join(context_blocks)
