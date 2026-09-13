from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import Message, MessageRole


class MessageRepository:
    """Repository for Message entity.
    MANDATORY: Every query MUST enforce company_id scoping for tenant isolation.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        conversation_id: uuid.UUID,
        company_id: uuid.UUID,
        role: MessageRole,
        content: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            company_id=company_id,
            role=role,
            content=content,
            citations=citations or [],
            message_metadata=metadata or {},
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_messages(
        self,
        conversation_id: uuid.UUID,
        company_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Message]:
        """Fetches messages for a conversation in chronological order."""
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.company_id == company_id,
            )
            .order_by(asc(Message.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_history(
        self,
        conversation_id: uuid.UUID,
        company_id: uuid.UUID,
        limit: int = 10,
    ) -> List[Message]:
        """Fetches the most recent messages for LLM context, ordered chronologically ascending."""
        subquery = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.company_id == company_id,
            )
            .order_by(desc(Message.created_at))
            .limit(limit)
            .subquery()
        )
        stmt = select(Message).from_statement(
            select(Message).where(Message.id.in_(select(subquery.c.id))).order_by(asc(Message.created_at))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
