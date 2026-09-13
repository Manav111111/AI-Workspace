from abc import ABC, abstractmethod
import os
import uuid
from typing import Optional
from app.core.config import settings
from app.core.exceptions import ValidationException


class StorageService(ABC):
    """Abstract interface for document file storage."""

    @abstractmethod
    async def save(self, company_id: uuid.UUID, original_filename: str, content: bytes) -> str:
        """Saves content and returns the storage path/key."""
        pass

    @abstractmethod
    async def get(self, storage_path: str) -> bytes:
        """Retrieves content from storage."""
        pass

    @abstractmethod
    async def delete(self, storage_path: str) -> bool:
        """Deletes file from storage."""
        pass

    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """Checks if file exists in storage."""
        pass


class LocalStorageService(StorageService):
    """Local filesystem storage implementation with strict directory traversal prevention."""

    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = os.path.abspath(root_dir or settings.STORAGE_ROOT)
        os.makedirs(self.root_dir, exist_ok=True)

    def _resolve_safe_path(self, relative_or_absolute_path: str) -> str:
        target_path = os.path.abspath(
            relative_or_absolute_path if os.path.isabs(relative_or_absolute_path)
            else os.path.join(self.root_dir, relative_or_absolute_path)
        )
        if not target_path.startswith(self.root_dir):
            raise ValidationException("Illegal file storage path traversal attempt")
        return target_path

    async def save(self, company_id: uuid.UUID, original_filename: str, content: bytes) -> str:
        # Sanitize extension
        _, ext = os.path.splitext(original_filename)
        safe_ext = ext.lower()
        unique_filename = f"{uuid.uuid4()}{safe_ext}"

        company_dir = os.path.join(self.root_dir, str(company_id))
        os.makedirs(company_dir, exist_ok=True)

        full_path = os.path.join(company_dir, unique_filename)
        safe_full_path = self._resolve_safe_path(full_path)

        with open(safe_full_path, "wb") as f:
            f.write(content)

        return safe_full_path

    async def get(self, storage_path: str) -> bytes:
        safe_path = self._resolve_safe_path(storage_path)
        if not os.path.exists(safe_path):
            raise ValidationException(f"Stored file does not exist at {storage_path}")

        with open(safe_path, "rb") as f:
            return f.read()

    async def delete(self, storage_path: str) -> bool:
        try:
            safe_path = self._resolve_safe_path(storage_path)
            if os.path.exists(safe_path):
                os.remove(safe_path)
                return True
        except Exception:
            return False
        return False

    async def exists(self, storage_path: str) -> bool:
        try:
            safe_path = self._resolve_safe_path(storage_path)
            return os.path.exists(safe_path)
        except Exception:
            return False
