import logging

from supportagent.db.session import SessionLocal
from supportagent.memory.schemas import ChatMessage, ConversationThread, LongMemory
from supportagent.memory.store import (
    add_long_memory,
    add_message,
    ensure_conversation,
    get_short_memory,
    get_thread_messages as select_thread_messages,
    list_conversation_threads as select_conversation_threads,
    search_long_memories,
    delete_user_turn as delete_user_turn_row,
    update_user_message as update_user_message_row,
)
from supportagent.rag.embeddings import embed_texts, get_embedding_client

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "anonymous"


def load_memory_context(
    thread_id: str | None,
    user_id: str | None,
    question: str,
) -> tuple[list[ChatMessage], list[LongMemory]]:
    if not thread_id:
        return [], []

    user_id = user_id or DEFAULT_USER_ID
    try:
        with SessionLocal.begin() as session:
            ensure_conversation(session, thread_id, user_id)
            short_memory = get_short_memory(session, thread_id, user_id)
            query_embedding = embed_texts(get_embedding_client(), [question])[0]
            long_memories = search_long_memories(session, user_id, query_embedding)
        return short_memory, long_memories
    except Exception:
        logger.exception("memory_load_failed thread_id=%s user_id=%s", thread_id, user_id)
        return [], []


def get_thread_messages(
    thread_id: str,
    user_id: str,
    limit: int = 100,
) -> list[ChatMessage]:
    try:
        with SessionLocal() as session:
            return select_thread_messages(session, thread_id, user_id, limit=limit)
    except Exception:
        logger.exception("thread_messages_load_failed thread_id=%s user_id=%s", thread_id, user_id)
        return []


def list_conversation_threads(
    user_id: str,
    limit: int = 30,
) -> list[ConversationThread]:
    try:
        with SessionLocal() as session:
            return select_conversation_threads(session, user_id=user_id, limit=limit)
    except Exception:
        logger.exception("conversation_threads_load_failed user_id=%s", user_id)
        return []


def update_thread_user_message(
    thread_id: str,
    user_id: str,
    message_id: int,
    content: str,
) -> bool:
    try:
        with SessionLocal.begin() as session:
            return update_user_message_row(session, thread_id, user_id, message_id, content)
    except Exception:
        logger.exception("thread_message_update_failed thread_id=%s user_id=%s message_id=%s", thread_id, user_id, message_id)
        return False


def delete_thread_user_turn(
    thread_id: str,
    user_id: str,
    message_id: int,
) -> bool:
    try:
        with SessionLocal.begin() as session:
            return delete_user_turn_row(session, thread_id, user_id, message_id)
    except Exception:
        logger.exception("thread_turn_delete_failed thread_id=%s user_id=%s message_id=%s", thread_id, user_id, message_id)
        return False


def save_memory_turn(
    thread_id: str | None,
    user_id: str | None,
    question: str,
    answer: str,
) -> None:
    if not thread_id:
        return

    user_id = user_id or DEFAULT_USER_ID
    try:
        with SessionLocal.begin() as session:
            if not ensure_conversation(session, thread_id, user_id):
                logger.warning(
                    "thread_owner_mismatch thread_id=%s user_id=%s", thread_id, user_id
                )
                return
            add_message(session, thread_id, "user", question)
            add_message(session, thread_id, "assistant", answer)

            memory_text = (
                "Conversation memory for future personalization. "
                f"User asked: {question}\nAssistant answered: {answer}"
            )
            memory_embedding = embed_texts(get_embedding_client(), [memory_text])[0]
            add_long_memory(session, user_id, thread_id, memory_text, memory_embedding)
    except Exception:
        logger.exception("memory_save_failed thread_id=%s user_id=%s", thread_id, user_id)


def record_mcp_action_turn(
    thread_id: str | None,
    user_id: str | None,
    question: str,
    summary: str,
) -> None:
    """Persist a manual MCP tool/action call (debug panel, Actions tab, or a
    confirmed calendar-action card) as a chat turn, so it survives a reload.
    These calls bypass answer_with_agent and would otherwise only exist in
    mcp_tool_audit_logs, which has no thread_id column.
    """
    if not thread_id:
        return

    user_id = user_id or DEFAULT_USER_ID
    try:
        with SessionLocal.begin() as session:
            if not ensure_conversation(session, thread_id, user_id):
                logger.warning(
                    "thread_owner_mismatch thread_id=%s user_id=%s", thread_id, user_id
                )
                return
            add_message(session, thread_id, "user", question)
            add_message(session, thread_id, "assistant", summary)
    except Exception:
        logger.exception("mcp_action_turn_save_failed thread_id=%s user_id=%s", thread_id, user_id)
