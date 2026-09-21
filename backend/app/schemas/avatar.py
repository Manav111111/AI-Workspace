from enum import Enum
import re
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AvatarEmotion(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    FRIENDLY = "friendly"
    CONFIDENT = "confident"
    CURIOUS = "curious"
    THINKING = "thinking"
    CONCERNED = "concerned"
    EXCITED = "excited"
    APOLOGETIC = "apologetic"
    SERIOUS = "serious"


class AvatarGesture(str, Enum):
    NONE = "none"
    SMALL_NOD = "small_nod"
    THINKING = "thinking"
    OPEN_HAND = "open_hand"
    EXPLAIN = "explain"
    POINT = "point"
    WELCOME = "welcome"
    AGREE = "agree"
    DISAGREE = "disagree"
    SHOULDER_SHIFT = "shoulder_shift"


class AvatarGaze(str, Enum):
    DIRECT = "direct"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    IDLE = "idle"
    GLANCE_AWAY = "glance_away"


class AvatarState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    WORKING = "working"
    INQUIRING = "inquiring"
    INTERRUPTED = "interrupted"


# Keys that are strictly forbidden in presentation metadata to prevent script/URL injection
FORBIDDEN_METADATA_KEYS = {"javascript", "execute", "url", "script", "code", "eval", "src", "onclick"}


class PresentationMetadata(BaseModel):
    """Controlled, validated presentation metadata schema for Phase 7.
    Strictly sanitizes LLM or engine outputs to ensure presentation safety.
    Guarantees:
    - Never executes arbitrary scripts or loads untrusted URLs.
    - Clamps intensities between 0.0 and 1.0.
    - Bounded durations between 100ms and 10,000ms.
    - Graceful fallback on invalid/malformed values.
    """
    emotion: AvatarEmotion = AvatarEmotion.NEUTRAL
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    duration_ms: int = Field(default=2000, ge=100, le=10000)
    gesture: AvatarGesture = AvatarGesture.NONE
    gaze: AvatarGaze = AvatarGaze.DIRECT

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def sanitize_and_clamp(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return {}

        sanitized: Dict[str, Any] = {}
        for key, value in data.items():
            lower_key = str(key).lower().strip()
            if lower_key in FORBIDDEN_METADATA_KEYS:
                # Discard unsafe keys
                continue
            if isinstance(value, str):
                # Discard script tags or javascript protocols if present in any string value
                if re.search(r"<script|javascript:|eval\(", value, re.IGNORECASE):
                    continue
            sanitized[lower_key] = value

        # Emotion normalization
        raw_emotion = sanitized.get("emotion", "neutral")
        if isinstance(raw_emotion, AvatarEmotion):
            sanitized["emotion"] = raw_emotion
        else:
            val = str(getattr(raw_emotion, "value", raw_emotion)).lower().strip()
            try:
                sanitized["emotion"] = AvatarEmotion(val)
            except ValueError:
                sanitized["emotion"] = AvatarEmotion.NEUTRAL

        # Gesture normalization
        raw_gesture = sanitized.get("gesture", "none")
        if isinstance(raw_gesture, AvatarGesture):
            sanitized["gesture"] = raw_gesture
        else:
            val = str(getattr(raw_gesture, "value", raw_gesture)).lower().strip()
            try:
                sanitized["gesture"] = AvatarGesture(val)
            except ValueError:
                sanitized["gesture"] = AvatarGesture.NONE

        # Gaze normalization
        raw_gaze = sanitized.get("gaze", "direct")
        if isinstance(raw_gaze, AvatarGaze):
            sanitized["gaze"] = raw_gaze
        else:
            val = str(getattr(raw_gaze, "value", raw_gaze)).lower().strip()
            try:
                sanitized["gaze"] = AvatarGaze(val)
            except ValueError:
                sanitized["gaze"] = AvatarGaze.DIRECT

        # Intensity clamping
        try:
            intensity = float(sanitized.get("intensity", 0.5))
            sanitized["intensity"] = max(0.0, min(1.0, intensity))
        except (ValueError, TypeError):
            sanitized["intensity"] = 0.5

        # Duration bounds
        try:
            duration = int(sanitized.get("duration_ms", 2000))
            sanitized["duration_ms"] = max(100, min(10000, duration))
        except (ValueError, TypeError):
            sanitized["duration_ms"] = 2000

        return sanitized


class AvatarEventEnvelope(BaseModel):
    """Standardized Avatar Event Protocol Version 2 Envelope.
    Preserves backwards compatibility with Phase 6 clients while adding protocol versioning.
    """
    protocol_version: int = Field(default=2, description="Avatar Event Protocol version (v2 for Phase 7)")
    type: str = Field(..., description="Event type string")
    sequence: int = Field(..., ge=1, description="Monotonically increasing sequence number")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp of event generation")
    session_id: Optional[str] = Field(None, description="Public session ID")
    generation_id: Optional[str] = Field(None, description="Active turn generation ID for stale-event discarding")
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Event-specific payload")

    model_config = ConfigDict(extra="allow")


def map_conversation_context_to_presentation(
    reply_text: str,
    tool_activity: Optional[list] = None,
    pending_confirmation: Optional[dict] = None,
    user_query: Optional[str] = None,
) -> PresentationMetadata:
    """Deterministic presentation state mapping based on conversation context.
    The AI Employee brain remains the single source of truth;
    this mapping translates conversational results into controlled avatar presentation states.
    """
    # 1. Action confirmation requested -> Inquiring / Curious
    if pending_confirmation:
        return PresentationMetadata(
            emotion=AvatarEmotion.CURIOUS,
            intensity=0.7,
            gesture=AvatarGesture.SMALL_NOD,
            gaze=AvatarGaze.DIRECT,
            duration_ms=3000,
        )

    # 2. Tool activity present -> Working / Confident
    if tool_activity and len(tool_activity) > 0:
        return PresentationMetadata(
            emotion=AvatarEmotion.CONFIDENT,
            intensity=0.6,
            gesture=AvatarGesture.EXPLAIN,
            gaze=AvatarGaze.SPEAKING,
            duration_ms=2500,
        )

    # 3. Text sentiment / keywords heuristic
    lower_text = (reply_text or "").lower()
    if any(w in lower_text for w in ["sorry", "apologize", "unfortunately", "cannot find", "unable"]):
        return PresentationMetadata(
            emotion=AvatarEmotion.APOLOGETIC,
            intensity=0.6,
            gesture=AvatarGesture.SHOULDER_SHIFT,
            gaze=AvatarGaze.GLANCE_AWAY,
            duration_ms=2200,
        )

    if any(w in lower_text for w in ["great", "awesome", "perfect", "glad to", "welcome", "hello", "hi "]):
        return PresentationMetadata(
            emotion=AvatarEmotion.FRIENDLY,
            intensity=0.7,
            gesture=AvatarGesture.WELCOME,
            gaze=AvatarGaze.DIRECT,
            duration_ms=2500,
        )

    if any(w in lower_text for w in ["note", "important", "remember", "specifically"]):
        return PresentationMetadata(
            emotion=AvatarEmotion.SERIOUS,
            intensity=0.5,
            gesture=AvatarGesture.SMALL_NOD,
            gaze=AvatarGaze.DIRECT,
            duration_ms=2000,
        )

    # Default friendly & natural speaking posture
    return PresentationMetadata(
        emotion=AvatarEmotion.FRIENDLY,
        intensity=0.5,
        gesture=AvatarGesture.NONE,
        gaze=AvatarGaze.SPEAKING,
        duration_ms=2000,
    )
