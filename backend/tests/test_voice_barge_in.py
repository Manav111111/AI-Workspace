import json
import uuid
import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_employee import AIEmployee, AIEmployeeStatus
from app.models.company import Company
from app.models.conversation import Conversation
from app.models.public_session import PublicChatSession
from app.services.public_runtime.security import hash_token
from app.services.voice.mock_providers import MockSTTProvider, MockTTSProvider
from app.services.voice.runtime import VoiceRuntimeManager


@pytest.mark.asyncio
async def test_voice_barge_in_cancellation(db_session: AsyncSession):
    company = Company(name="Barge In Test Co", slug=f"bargein-{uuid.uuid4().hex[:6]}")
    db_session.add(company)
    await db_session.flush()

    emp = AIEmployee(
        company_id=company.id,
        name="BargeIn Bot",
        role="Assistant",
        public_id=f"pub_voice_{uuid.uuid4().hex[:8]}",
        is_published=True,
        status=AIEmployeeStatus.ACTIVE,
        allowed_domains=["*"],
    )
    db_session.add(emp)
    await db_session.flush()

    conv = Conversation(company_id=company.id, ai_employee_id=emp.id, title="BargeIn Conv")
    db_session.add(conv)
    await db_session.flush()

    import datetime
    raw_token = f"sess_pub_{uuid.uuid4().hex}"
    pub_session = PublicChatSession(
        company_id=company.id,
        ai_employee_id=emp.id,
        conversation_id=conv.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24),
    )
    db_session.add(pub_session)
    await db_session.commit()

    sent_frames = []
    mock_ws = AsyncMock()
    mock_ws.client.host = "127.0.0.1"

    async def capture_send_text(text: str):
        sent_frames.append(json.loads(text))

    mock_ws.send_text.side_effect = capture_send_text

    manager = VoiceRuntimeManager(
        websocket=mock_ws,
        session=db_session,
        stt_provider=MockSTTProvider(),
        tts_provider=MockTTSProvider(),
    )

    await manager.authenticate_handshake(raw_token)

    # Simulate AI speaking state
    manager.is_ai_speaking = True
    manager.active_generation_id = "gen_123"

    # User interrupts
    await manager.handle_barge_in()

    assert manager.is_ai_speaking is False
    assert manager.interruptions_count == 1

    # Verify "interrupted" frame sent to browser
    interrupted_frame = next((f for f in sent_frames if f.get("type") == "interrupted"), None)
    assert interrupted_frame is not None
    assert interrupted_frame["generation_id"] == "gen_123"
