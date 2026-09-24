from typing import List
from app.core.exceptions import ValidationException
from app.services.parsers.base import DocumentParser, ParsedSection

try:
    import pymupdf as fitz  # PyMuPDF modern import
except ImportError:
    try:
        import fitz  # Legacy fallback
    except ImportError:
        fitz = None


class PDFParser(DocumentParser):
    def can_parse(self, file_type: str) -> bool:
        return file_type.lower() in ["pdf", ".pdf", "application/pdf"]

    def parse(self, content: bytes, original_filename: str) -> List[ParsedSection]:
        if fitz is None:
            raise ValidationException(
                "PyMuPDF (fitz) is not installed in the current Python environment. "
                "Please run: pip install pymupdf"
            )

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            raise ValidationException(f"Failed to read PDF document: {str(e)}")

        sections: List[ParsedSection] = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            if text:
                sections.append(
                    ParsedSection(
                        content=text,
                        metadata={
                            "page": page_num + 1,
                            "source": original_filename,
                            "file_type": "pdf",
                        },
                    )
                )

        doc.close()
        if not sections:
            raise ValidationException("PDF contains no extractable text")

        return sections
