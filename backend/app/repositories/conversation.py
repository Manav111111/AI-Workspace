from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation


class ConversationRepository:
    """Repository for Conversation entity.
    MANDATORY: Every query MUST enforce company_id scoping for tenant isolation.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        company_id: uuid.UUID,
        ai_employee_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        title: str = "New Conversation",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Conversation:
        conversation = Conversation(
            company_id=company_id,
            ai_employee_id=ai_employee_id,
            user_id=user_id,
            title=title,
            conversation_metadata=metadata or {},
        )
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get_by_id(self, conversation_id: uuid.UUID, company_id: uuid.UUID) -> Optional[Conversation]:
        """Fetches a conversation by ID, strictly filtered by tenant company_id."""
        stmt = (
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.company_id == company_id,
                Conversation.is_active == True,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list(
        self,
        company_id: uuid.UUID,
        ai_employee_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        """Lists conversations for a tenant, optionally filtered by AI Employee."""
        stmt = (
            select(Conversation)
            .where(
                Conversation.company_id == company_id,
                Conversation.is_active == True,
            )
        )
        if ai_employee_id:
            stmt = stmt.where(Conversation.ai_employee_id == ai_employee_id)

        stmt = stmt.order_by(desc(Conversation.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_title(
        self,
        conversation_id: uuid.UUID,
        company_id: uuid.UUID,
        title: str,
    ) -> Optional[Conversation]:
        conversation = await self.get_by_id(conversation_id, company_id)
        if not conversation:
            return None
        conversation.title = title
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def delete(self, conversation_id: uuid.UUID, company_id: uuid.UUID) -> bool:
        """Soft deletes conversation, scoped to company_id."""
        conversation = await self.get_by_id(conversation_id, company_id)
        if not conversation:
            return False
        conversation.is_active = False
        await self.session.commit()
        return True
