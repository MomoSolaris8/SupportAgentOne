import logging

from supportagent.memory.schemas import ChatMessage, ConversationThread, LongMemory
from supportagent.memory.store import (
    add_long_memory,
    add_message,
    create_memory_schema,
    ensure_conversation,
    get_short_memory,
    get_thread_messages as select_thread_messages,
    list_conversation_threads as select_conversation_threads,
    search_long_memories,
    delete_user_turn as delete_user_turn_row,
    update_user_message as update_user_message_row,
)
from supportagent.rag.embeddings import embed_texts, get_embedding_client
from supportagent.rag.vector_store import get_connection

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
    conn = get_connection()
    try:
        create_memory_schema(conn)
        ensure_conversation(conn, thread_id, user_id)
        short_memory = get_short_memory(conn, thread_id)
        query_embedding = embed_texts(get_embedding_client(), [question])[0]
        long_memories = search_long_memories(conn, user_id, query_embedding)
        conn.commit()
        return short_memory, long_memories
    except Exception:
        logger.exception("memory_load_failed thread_id=%s user_id=%s", thread_id, user_id)
        conn.rollback()
        return [], []
    finally:
        conn.close()


def get_thread_messages(
    thread_id: str,
    user_id: str,
    limit: int = 100,
) -> list[ChatMessage]:
    conn = get_connection()
    try:
        create_memory_schema(conn)
        messages = select_thread_messages(conn, thread_id, user_id, limit=limit)
        conn.commit()
        return messages
    except Exception:
        logger.exception("thread_messages_load_failed thread_id=%s user_id=%s", thread_id, user_id)
        conn.rollback()
        return []
    finally:
        conn.close()


def list_conversation_threads(
    user_id: str,
    limit: int = 30,
) -> list[ConversationThread]:
    conn = get_connection()
    try:
        create_memory_schema(conn)
        threads = select_conversation_threads(conn, user_id=user_id, limit=limit)
        conn.commit()
        return threads
    except Exception:
        logger.exception("conversation_threads_load_failed user_id=%s", user_id)
        conn.rollback()
        return []
    finally:
        conn.close()


def update_thread_user_message(
    thread_id: str,
    user_id: str,
    message_id: int,
    content: str,
) -> bool:
    conn = get_connection()
    try:
        create_memory_schema(conn)
        updated = update_user_message_row(conn, thread_id, user_id, message_id, content)
        conn.commit()
        return updated
    except Exception:
        logger.exception("thread_message_update_failed thread_id=%s user_id=%s message_id=%s", thread_id, user_id, message_id)
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_thread_user_turn(
    thread_id: str,
    user_id: str,
    message_id: int,
) -> bool:
    conn = get_connection()
    try:
        create_memory_schema(conn)
        deleted = delete_user_turn_row(conn, thread_id, user_id, message_id)
        conn.commit()
        return deleted
    except Exception:
        logger.exception("thread_turn_delete_failed thread_id=%s user_id=%s message_id=%s", thread_id, user_id, message_id)
        conn.rollback()
        return False
    finally:
        conn.close()


def save_memory_turn(
    thread_id: str | None,
    user_id: str | None,
    question: str,
    answer: str,
) -> None:
    if not thread_id:
        return

    user_id = user_id or DEFAULT_USER_ID
    conn = get_connection()
    try:
        create_memory_schema(conn)
        ensure_conversation(conn, thread_id, user_id)
        add_message(conn, thread_id, "user", question)
        add_message(conn, thread_id, "assistant", answer)

        memory_text = (
            "Conversation memory for future personalization. "
            f"User asked: {question}\nAssistant answered: {answer}"
        )
        memory_embedding = embed_texts(get_embedding_client(), [memory_text])[0]
        add_long_memory(conn, user_id, thread_id, memory_text, memory_embedding)
        conn.commit()
    except Exception:
        logger.exception("memory_save_failed thread_id=%s user_id=%s", thread_id, user_id)
        conn.rollback()
    finally:
        conn.close()


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
    conn = get_connection()
    try:
        create_memory_schema(conn)
        ensure_conversation(conn, thread_id, user_id)
        add_message(conn, thread_id, "user", question)
        add_message(conn, thread_id, "assistant", summary)
        conn.commit()
    except Exception:
        logger.exception("mcp_action_turn_save_failed thread_id=%s user_id=%s", thread_id, user_id)
        conn.rollback()
    finally:
        conn.close()
