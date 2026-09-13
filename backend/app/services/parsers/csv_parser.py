import csv
import io
from typing import List
from app.core.exceptions import ValidationException
from app.services.parsers.base import DocumentParser, ParsedSection


class CSVParser(DocumentParser):
    def can_parse(self, file_type: str) -> bool:
        return file_type.lower() in ["csv", ".csv", "text/csv", "application/csv"]

    def parse(self, content: bytes, original_filename: str) -> List[ParsedSection]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception as e:
                raise ValidationException(f"Failed to decode CSV file: {str(e)}")

        f = io.StringIO(text.strip())
        reader = csv.reader(f)
        try:
            headers = next(reader, None)
        except Exception as e:
            raise ValidationException(f"Failed to read CSV headers: {str(e)}")

        if not headers:
            raise ValidationException("CSV file contains no headers or data")

        headers = [h.strip() for h in headers]
        sections: List[ParsedSection] = []

        for row_idx, row in enumerate(reader):
            if not any(cell.strip() for cell in row):
                continue

            # Format each row into semantic representation
            row_items = []
            for col_idx, col_name in enumerate(headers):
                val = row[col_idx].strip() if col_idx < len(row) else ""
                if val:
                    row_items.append(f"{col_name}: {val}")

            if row_items:
                serialized_row = " | ".join(row_items)
                sections.append(
                    ParsedSection(
                        content=serialized_row,
                        metadata={
                            "row_index": row_idx + 1,
                            "source": original_filename,
                            "file_type": "csv",
                        },
                    )
                )

        if not sections:
            raise ValidationException("CSV file contains no readable data rows")

        return sections
