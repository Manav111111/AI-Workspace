import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.repositories.ai_employee import AIEmployeeRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository

logger = logging.getLogger("app.services.conversation")


class ConversationService:
    """Service managing conversation lifecycle and message queries."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.message_repo = MessageRepository(session)
        self.employee_repo = AIEmployeeRepository(session)

    async def create_conversation(
        self,
        company_id: uuid.UUID,
        ai_employee_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        title: Optional[str] = None,
    ) -> Conversation:
        # Verify AI Employee belongs to the company
        employee = await self.employee_repo.get_by_tenant(company_id=company_id, employee_id=ai_employee_id)
        if not employee:
            raise NotFoundException("AI Employee not found in your company")

        conv_title = title or f"Chat with {employee.name}"
        return await self.conversation_repo.create(
            company_id=company_id,
            ai_employee_id=ai_employee_id,
            user_id=user_id,
            title=conv_title,
        )

    async def get_conversation(
        self,
        conversation_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> Conversation:
        conversation = await self.conversation_repo.get_by_id(conversation_id, company_id)
        if not conversation:
            raise NotFoundException("Conversation not found")
        return conversation

    async def list_conversations(
        self,
        company_id: uuid.UUID,
        ai_employee_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        return await self.conversation_repo.list(
            company_id=company_id,
            ai_employee_id=ai_employee_id,
            limit=limit,
            offset=offset,
        )

    async def delete_conversation(
        self,
        conversation_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        deleted = await self.conversation_repo.delete(conversation_id, company_id)
        if not deleted:
            raise NotFoundException("Conversation not found")

    async def get_messages(
        self,
        conversation_id: uuid.UUID,
        company_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Message]:
        # Validate conversation ownership
        await self.get_conversation(conversation_id, company_id)
        return await self.message_repo.get_messages(
            conversation_id=conversation_id,
            company_id=company_id,
            limit=limit,
            offset=offset,
        )
