from typing import List
from app.core.exceptions import ValidationException
from app.services.parsers.base import DocumentParser, ParsedSection


class TXTParser(DocumentParser):
    def can_parse(self, file_type: str) -> bool:
        return file_type.lower() in ["txt", "text", ".txt", "text/plain"]

    def parse(self, content: bytes, original_filename: str) -> List[ParsedSection]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception as e:
                raise ValidationException(f"Failed to decode text file: {str(e)}")

        text = text.strip()
        if not text:
            raise ValidationException("Text file is empty")

        # Split into paragraphs by double newlines
        raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        sections: List[ParsedSection] = []

        for idx, para in enumerate(raw_paragraphs):
            sections.append(
                ParsedSection(
                    content=para,
                    metadata={
                        "paragraph_index": idx + 1,
                        "source": original_filename,
                        "file_type": "txt",
                    },
                )
            )

        return sections if sections else [
            ParsedSection(
                content=text,
                metadata={"source": original_filename, "file_type": "txt"},
            )
        ]
