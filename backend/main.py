"""Root entrypoint alias allowing 'uvicorn main:app --reload' to work directly from the backend directory."""
from app.main import app

__all__ = ["app"]
