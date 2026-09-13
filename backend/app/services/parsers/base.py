from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ParsedSection:
    """Represents an extracted structural unit of a document."""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentParser(ABC):
    """Abstract interface for file-format specific parsers."""

    @abstractmethod
    def can_parse(self, file_type: str) -> bool:
        """Determines if this parser supports the given file extension or type."""
        pass

    @abstractmethod
    def parse(self, content: bytes, original_filename: str) -> List[ParsedSection]:
        """Parses file raw bytes and returns a list of structured sections."""
        pass
