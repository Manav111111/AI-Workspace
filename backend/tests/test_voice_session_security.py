import json
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_employee import AIEmployee, AIEmployeeStatus
from app.models.company import Company
from app.models.conversation import Conversation
from app.models.public_session import PublicChatSession
from app.services.public_runtime.security import hash_token


@pytest.mark.asyncio
async def test_get_available_voices_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/voice/voices")
    assert response.status_code == 200
    data = response.json()
    assert "voices" in data
    assert "provider" in data
    assert len(data["voices"]) > 0


@pytest.mark.asyncio
async def test_voice_session_handshake_security(
    client: AsyncClient,
    db_session: AsyncSession,
):
    # Setup company, published employee, and public session
    company = Company(
        name="Voice Security Test Co",
        slug=f"voicesec-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(company)
    await db_session.flush()

    emp = AIEmployee(
        company_id=company.id,
        name="Voice Bot",
        role="Voice Assistant",
        public_id=f"pub_voice_{uuid.uuid4().hex[:8]}",
        is_published=True,
        status=AIEmployeeStatus.ACTIVE,
        allowed_domains=["*"],
        voice_config={"voice_id": "mock_aria", "speed": 1.0},
    )
    db_session.add(emp)
    await db_session.flush()

    conv = Conversation(
        company_id=company.id,
        ai_employee_id=emp.id,
        title="Voice Conversation",
    )
    db_session.add(conv)
    await db_session.flush()

    import datetime
    raw_token = f"sess_pub_{uuid.uuid4().hex}"
    pub_session = PublicChatSession(
        company_id=company.id,
        ai_employee_id=emp.id,
        conversation_id=conv.id,
        token_hash=hash_token(raw_token),
        origin_domain="https://example.com",
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24),
    )
    db_session.add(pub_session)
    await db_session.commit()

    # Verify voice session security manager directly
    from app.services.voice.runtime import VoiceRuntimeManager, VoiceSessionSecurityException
    from unittest.mock import AsyncMock

    mock_ws = AsyncMock()
    mock_ws.client.host = "127.0.0.1"

    manager = VoiceRuntimeManager(websocket=mock_ws, session=db_session)
    
    # 1. Invalid token should raise VoiceSessionSecurityException
    with pytest.raises(Exception):
        await manager.authenticate_handshake("invalid_token_xyz")

    # 2. Valid token should succeed
    resolved = await manager.authenticate_handshake(raw_token)
    assert resolved.id == pub_session.id
    assert manager.is_authenticated is True
    assert manager.ai_employee.id == emp.id
    assert manager.voice_session_record is not None

    # 3. Second auth call on same socket MUST be rejected (single auth invariant)
    with pytest.raises(VoiceSessionSecurityException, match="already authenticated"):
        await manager.authenticate_handshake(raw_token)
