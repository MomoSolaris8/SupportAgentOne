from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChatMessage:
    id: int | None
    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True)
class LongMemory:
    id: int
    content: str
    kind: str
    distance: float


@dataclass(frozen=True)
class ConversationThread:
    thread_id: str
    title: str
    updated_at: datetime
    message_count: int
