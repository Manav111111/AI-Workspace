# Import all models here for Alembic target_metadata discovery
from app.models.base import Base
from app.models.user import User
from app.models.company import Company
from app.models.membership import Membership
from app.models.ai_employee import AIEmployee
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.conversation import Conversation
from app.models.message import Message

__all__ = [
    "Base",
    "User",
    "Company",
    "Membership",
    "AIEmployee",
    "KnowledgeBase",
    "Document",
    "DocumentChunk",
    "Conversation",
    "Message",
]
