from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from supportagent.db.models import Conversation, ConversationMessage
from supportagent.db.models import LongMemory as LongMemoryRow
from supportagent.memory.schemas import ChatMessage, ConversationThread, LongMemory

SHORT_MEMORY_LIMIT = 6
LONG_MEMORY_LIMIT = 3


def _to_chat_message(message: ConversationMessage) -> ChatMessage:
    return ChatMessage(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


def ensure_conversation(session: Session, thread_id: str, user_id: str) -> None:
    stmt = insert(Conversation).values(thread_id=thread_id, user_id=user_id)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Conversation.thread_id],
        set_={"user_id": stmt.excluded.user_id, "updated_at": func.now()},
    )
    session.execute(stmt)


def get_short_memory(
    session: Session,
    thread_id: str,
    limit: int = SHORT_MEMORY_LIMIT,
) -> list[ChatMessage]:
    messages = session.scalars(
        select(ConversationMessage)
        .where(ConversationMessage.thread_id == thread_id)
        .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
        .limit(limit)
    ).all()
    return [_to_chat_message(message) for message in reversed(messages)]


def get_thread_messages(
    session: Session,
    thread_id: str,
    user_id: str,
    limit: int = 100,
) -> list[ChatMessage]:
    messages = session.scalars(
        select(ConversationMessage)
        .join(Conversation, Conversation.thread_id == ConversationMessage.thread_id)
        .where(
            ConversationMessage.thread_id == thread_id,
            Conversation.user_id == user_id,
        )
        .order_by(ConversationMessage.created_at, ConversationMessage.id)
        .limit(limit)
    )
    return [_to_chat_message(message) for message in messages]


def list_conversation_threads(
    session: Session,
    user_id: str,
    limit: int = 30,
) -> list[ConversationThread]:
    first_question = func.min(ConversationMessage.content).filter(
        ConversationMessage.role == "user"
    )
    title = func.coalesce(func.nullif(func.left(first_question, 80), ""), "New chat")
    rows = session.execute(
        select(
            Conversation.thread_id,
            title.label("title"),
            Conversation.updated_at,
            func.count(ConversationMessage.id).label("message_count"),
        )
        .outerjoin(
            ConversationMessage,
            ConversationMessage.thread_id == Conversation.thread_id,
        )
        .where(Conversation.user_id == user_id)
        .group_by(Conversation.thread_id, Conversation.updated_at)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    return [
        ConversationThread(
            thread_id=row.thread_id,
            title=row.title,
            updated_at=row.updated_at,
            message_count=row.message_count,
        )
        for row in rows
    ]


def add_message(session: Session, thread_id: str, role: str, content: str) -> None:
    session.add(ConversationMessage(thread_id=thread_id, role=role, content=content))


def _owned_question(
    session: Session,
    thread_id: str,
    user_id: str,
    message_id: int,
) -> ConversationMessage | None:
    return session.scalar(
        select(ConversationMessage)
        .join(Conversation, Conversation.thread_id == ConversationMessage.thread_id)
        .where(
            ConversationMessage.id == message_id,
            ConversationMessage.thread_id == thread_id,
            ConversationMessage.role == "user",
            Conversation.user_id == user_id,
        )
    )


def _delete_answer_after(session: Session, question: ConversationMessage) -> None:
    answer_id = session.scalar(
        select(ConversationMessage.id)
        .where(
            ConversationMessage.thread_id == question.thread_id,
            ConversationMessage.role == "assistant",
            ConversationMessage.id > question.id,
        )
        .order_by(ConversationMessage.id)
        .limit(1)
    )
    if answer_id is not None:
        session.execute(delete(ConversationMessage).where(ConversationMessage.id == answer_id))


def _touch_conversation(session: Session, thread_id: str) -> None:
    session.execute(
        update(Conversation)
        .where(Conversation.thread_id == thread_id)
        .values(updated_at=func.now())
    )


def update_user_message(
    session: Session,
    thread_id: str,
    user_id: str,
    message_id: int,
    content: str,
) -> bool:
    question = _owned_question(session, thread_id, user_id, message_id)
    if question is None:
        return False
    question.content = content
    _delete_answer_after(session, question)
    _touch_conversation(session, thread_id)
    return True


def delete_user_turn(
    session: Session,
    thread_id: str,
    user_id: str,
    message_id: int,
) -> bool:
    question = _owned_question(session, thread_id, user_id, message_id)
    if question is None:
        return False
    _delete_answer_after(session, question)
    session.delete(question)
    _touch_conversation(session, thread_id)
    return True


def search_long_memories(
    session: Session,
    user_id: str,
    query_embedding: list[float],
    limit: int = LONG_MEMORY_LIMIT,
) -> list[LongMemory]:
    distance = LongMemoryRow.embedding.cosine_distance(query_embedding)
    rows = session.execute(
        select(
            LongMemoryRow.id,
            LongMemoryRow.content,
            LongMemoryRow.kind,
            distance.label("distance"),
        )
        .where(LongMemoryRow.user_id == user_id)
        .order_by(distance)
        .limit(limit)
    )
    return [
        LongMemory(id=row.id, content=row.content, kind=row.kind, distance=row.distance)
        for row in rows
    ]


def add_long_memory(
    session: Session,
    user_id: str,
    thread_id: str,
    content: str,
    embedding: list[float],
    kind: str = "conversation_summary",
) -> None:
    session.add(
        LongMemoryRow(
            user_id=user_id,
            thread_id=thread_id,
            kind=kind,
            content=content,
            embedding=embedding,
            metadata_={"source": "supportagent", "created_by": "answer_with_agent"},
        )
    )
