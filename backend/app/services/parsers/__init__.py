import os
from typing import List
from app.core.exceptions import ValidationException
from app.services.parsers.base import DocumentParser, ParsedSection
from app.services.parsers.pdf_parser import PDFParser
from app.services.parsers.docx_parser import DOCXParser
from app.services.parsers.markdown_parser import MarkdownParser
from app.services.parsers.txt_parser import TXTParser
from app.services.parsers.csv_parser import CSVParser

PARSERS: List[DocumentParser] = [
    PDFParser(),
    DOCXParser(),
    MarkdownParser(),
    TXTParser(),
    CSVParser(),
]


def get_parser_for_file(filename_or_type: str) -> DocumentParser:
    """Finds the appropriate document parser based on file extension or mime type."""
    ext = os.path.splitext(filename_or_type)[1].lower()
    lookup = ext if ext else filename_or_type.lower()

    for parser in PARSERS:
        if parser.can_parse(lookup):
            return parser

    raise ValidationException(
        f"Unsupported file format '{lookup}'. Supported formats are: PDF, DOCX, Markdown, TXT, CSV."
    )


__all__ = [
    "DocumentParser",
    "ParsedSection",
    "PDFParser",
    "DOCXParser",
    "MarkdownParser",
    "TXTParser",
    "CSVParser",
    "get_parser_for_file",
]
