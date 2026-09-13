from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import TenantContext, get_tenant_context
from app.db.session import get_db
from app.schemas.conversation import (
    ChatResponse,
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from app.services.conversation import ConversationService
from app.services.conversation_engine import ConversationEngine

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Creates a new conversation with an AI Employee within the active tenant."""
    service = ConversationService(session)
    conversation = await service.create_conversation(
        company_id=tenant.company_id,
        ai_employee_id=payload.ai_employee_id,
        user_id=tenant.user_id,
        title=payload.title,
    )
    return ConversationResponse.model_validate(conversation)


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    ai_employee_id: Optional[uuid.UUID] = Query(None, description="Filter by AI Employee"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[ConversationResponse]:
    """Lists conversations belonging to the active tenant."""
    service = ConversationService(session)
    conversations = await service.list_conversations(
        company_id=tenant.company_id,
        ai_employee_id=ai_employee_id,
        limit=limit,
        offset=offset,
    )
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get("/{id}", response_model=ConversationResponse)
async def get_conversation(
    id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Gets conversation details, strictly verifying tenant ownership."""
    service = ConversationService(session)
    conversation = await service.get_conversation(
        conversation_id=id,
        company_id=tenant.company_id,
    )
    return ConversationResponse.model_validate(conversation)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Deletes a conversation within the active tenant."""
    service = ConversationService(session)
    await service.delete_conversation(
        conversation_id=id,
        company_id=tenant.company_id,
    )


@router.get("/{id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[MessageResponse]:
    """Retrieves chronological message history for a conversation in the active tenant."""
    service = ConversationService(session)
    messages = await service.get_messages(
        conversation_id=id,
        company_id=tenant.company_id,
        limit=limit,
        offset=offset,
    )
    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{id}/messages", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def send_message(
    id: uuid.UUID,
    payload: MessageCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Sends a user message, runs grounded RAG retrieval, and generates an AI Employee response."""
    engine = ConversationEngine(session)
    engine_resp = await engine.respond(
        company_id=tenant.company_id,
        conversation_id=id,
        user_query=payload.content,
        user_id=tenant.user_id,
    )

    return ChatResponse(
        user_message=MessageResponse.model_validate(engine_resp.user_message),
        assistant_message=MessageResponse.model_validate(engine_resp.assistant_message),
        citations=engine_resp.citations,
        metrics=engine_resp.metrics,
    )
