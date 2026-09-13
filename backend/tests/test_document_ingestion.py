import uuid
import pytest
from app.services.chunking import ChunkingService
from app.services.cleaning import TextCleaner
from app.services.parsers.csv_parser import CSVParser
from app.services.parsers.markdown_parser import MarkdownParser
from app.services.parsers.txt_parser import TXTParser


def test_text_cleaner_normalizes_artifacts():
    raw = "Hello   world!\r\n\r\n\r\nThis is a test  of multi-\ntenant systems.\u00a0"
    cleaned = TextCleaner.clean(raw)
    assert "Hello   world!" in cleaned
    assert "\r" not in cleaned
    assert "\n\n\n" not in cleaned
    assert "multi-tenant" in cleaned
    assert "\u00a0" not in cleaned


def test_csv_parser_semantic_rows():
    csv_bytes = b"Plan,Price,Features\nBasic,$10,Chat only\nEnterprise,$99,Full AI Avatar"
    parser = CSVParser()
    sections = parser.parse(csv_bytes, "plans.csv")
    assert len(sections) == 2
    assert "Plan: Basic | Price: $10 | Features: Chat only" == sections[0].content
    assert sections[0].metadata["row_index"] == 1
    assert "Plan: Enterprise | Price: $99 | Features: Full AI Avatar" == sections[1].content


def test_markdown_parser_structural_headings():
    md_bytes = b"# Main Title\nIntroductory text.\n\n## Sub Title\nDetails text."
    parser = MarkdownParser()
    sections = parser.parse(md_bytes, "doc.md")
    assert len(sections) == 2
    assert sections[0].metadata["section"] == "Main Title"
    assert "Introductory text." in sections[0].content
    assert sections[1].metadata["section"] == "Sub Title"
    assert "Details text." in sections[1].content


def test_chunking_service_metadata_and_indices():
    parser = MarkdownParser()
    sections = parser.parse(b"# Policy\nShort section.", "policy.md")
    chunker = ChunkingService(chunk_size=100, chunk_overlap=20)
    company_id = uuid.uuid4()
    kb_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    chunks = chunker.chunk_sections(
        sections=sections,
        company_id=company_id,
        knowledge_base_id=kb_id,
        document_id=doc_id,
    )
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_index == 0
    assert chunk.metadata["company_id"] == str(company_id)
    assert chunk.metadata["knowledge_base_id"] == str(kb_id)
    assert chunk.metadata["document_id"] == str(doc_id)
    assert chunk.metadata["section"] == "Policy"
