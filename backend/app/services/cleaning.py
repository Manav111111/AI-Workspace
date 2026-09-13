import re


class TextCleaner:
    """Normalizes extracted text content without rewriting semantic meaning."""

    @staticmethod
    def clean(text: str) -> str:
        if not text:
            return ""

        # Remove null bytes and non-printable control characters (except newline, tab)
        text = "".join(ch for ch in text if ch in ("\n", "\t", "\r") or (ord(ch) >= 32 and ord(ch) != 127))

        # Normalize carriage returns
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace 3 or more consecutive newlines with two newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Normalize horizontal tabs and non-breaking spaces
        text = text.replace("\u00a0", " ").replace("\t", "    ")

        # Strip trailing whitespace on each line
        lines = [re.sub(r"[ \t]+$", "", line) for line in text.split("\n")]
        text = "\n".join(lines)

        # Fix broken hyphenated words at end of line (e.g. "multi-\ntenant" -> "multi-tenant")
        text = re.sub(r"(\w+)-\n(\w+)", r"\1-\2", text)

        return text.strip()
