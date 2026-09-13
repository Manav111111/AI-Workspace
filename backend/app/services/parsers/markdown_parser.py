import re
from typing import List
from app.core.exceptions import ValidationException
from app.services.parsers.base import DocumentParser, ParsedSection


class MarkdownParser(DocumentParser):
    def can_parse(self, file_type: str) -> bool:
        return file_type.lower() in ["md", "markdown", ".md", "text/markdown"]

    def parse(self, content: bytes, original_filename: str) -> List[ParsedSection]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception as e:
                raise ValidationException(f"Failed to decode Markdown file: {str(e)}")

        lines = text.splitlines()
        sections: List[ParsedSection] = []
        current_section = "Overview"
        current_lines: List[str] = []

        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

        for line in lines:
            match = header_pattern.match(line.strip())
            if match:
                if current_lines:
                    block_text = "\n".join(current_lines).strip()
                    if block_text:
                        sections.append(
                            ParsedSection(
                                content=block_text,
                                metadata={
                                    "section": current_section,
                                    "source": original_filename,
                                    "file_type": "md",
                                },
                            )
                        )
                    current_lines = []
                current_section = match.group(2).strip()
            else:
                current_lines.append(line)

        if current_lines:
            block_text = "\n".join(current_lines).strip()
            if block_text:
                sections.append(
                    ParsedSection(
                        content=block_text,
                        metadata={
                            "section": current_section,
                            "source": original_filename,
                            "file_type": "md",
                        },
                    )
                )

        if not sections:
            raise ValidationException("Markdown file contains no readable content")

        return sections
