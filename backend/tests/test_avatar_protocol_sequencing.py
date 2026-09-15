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
import datetime


@pytest.mark.asyncio
async def test_avatar_event_protocol_sequencing(db_session: AsyncSession):
    company = Company(name="Avatar Sequence Co", slug=f"avatarseq-{uuid.uuid4().hex[:6]}")
    db_session.add(company)
    await db_session.flush()

    emp = AIEmployee(
        company_id=company.id,
        name="Avatar Priya",
        role="Customer Representative",
        public_id=f"pub_avatar_{uuid.uuid4().hex[:8]}",
        is_published=True,
        status=AIEmployeeStatus.ACTIVE,
        allowed_domains=["*"],
        avatar_config={
            "model_id": "default_female",
            "expression_preset": "friendly",
            "camera_framing": "bust",
        },
        voice_config={"voice_id": "mock_aria", "speed": 1.0},
    )
    db_session.add(emp)
    await db_session.flush()

    conv = Conversation(company_id=company.id, ai_employee_id=emp.id, title="Avatar Session")
    db_session.add(conv)
    await db_session.flush()

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

    stt = MockSTTProvider(canned_transcript="Hello Priya, can you help me?")
    tts = MockTTSProvider()

    manager = VoiceRuntimeManager(
        websocket=mock_ws,
        session=db_session,
        stt_provider=stt,
        tts_provider=tts,
    )

    await manager.authenticate_handshake(raw_token)

    # Process audio utterance
    await manager.process_user_utterance(audio_data=b"\x00" * 3200, audio_format="webm")

    # Assert all frames adhere to AvatarEvent schema:
    # { type, sequence, timestamp, session_id, generation_id }
    assert len(sent_frames) > 0
    sequences = []
    for frame in sent_frames:
        assert "type" in frame
        assert "sequence" in frame
        assert "timestamp" in frame
        assert "session_id" in frame
        assert frame["session_id"] == str(pub_session.id)
        sequences.append(frame["sequence"])

    # Verify monotonic increasing sequence order
    assert sequences == sorted(sequences)
    assert len(set(sequences)) == len(sequences)  # All sequences unique
    assert sequences[0] == 1  # Started at 1
