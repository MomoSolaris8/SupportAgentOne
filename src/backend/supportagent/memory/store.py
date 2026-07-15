import json
import os

import psycopg

from supportagent.memory.schemas import ChatMessage, ConversationThread, LongMemory

SHORT_MEMORY_LIMIT = 6
LONG_MEMORY_LIMIT = 3


def create_memory_schema(conn: psycopg.Connection, dimensions: int | None = None) -> None:
    dimensions = dimensions or int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            thread_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id BIGSERIAL PRIMARY KEY,
            thread_id TEXT NOT NULL REFERENCES conversations(thread_id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS long_memories (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            thread_id TEXT REFERENCES conversations(thread_id) ON DELETE SET NULL,
            kind TEXT NOT NULL DEFAULT 'conversation_summary',
            content TEXT NOT NULL,
            embedding vector({dimensions}),
            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS conversation_messages_thread_created_idx
        ON conversation_messages (thread_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS long_memories_user_created_idx
        ON long_memories (user_id, created_at DESC)
        """
    )
    conn.commit()


def ensure_conversation(conn: psycopg.Connection, thread_id: str, user_id: str) -> None:
    conn.execute(
        """
        INSERT INTO conversations (thread_id, user_id)
        VALUES (%s, %s)
        ON CONFLICT (thread_id)
        DO UPDATE SET user_id = EXCLUDED.user_id, updated_at = now()
        """,
        (thread_id, user_id),
    )


def get_short_memory(
    conn: psycopg.Connection,
    thread_id: str,
    limit: int = SHORT_MEMORY_LIMIT,
) -> list[ChatMessage]:
    rows = conn.execute(
        """
        SELECT id, role, content, created_at
        FROM conversation_messages
        WHERE thread_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT %s
        """,
        (thread_id, limit),
    ).fetchall()
    return [
        ChatMessage(id=row[0], role=row[1], content=row[2], created_at=row[3])
        for row in reversed(rows)
    ]


def get_thread_messages(
    conn: psycopg.Connection,
    thread_id: str,
    user_id: str,
    limit: int = 100,
) -> list[ChatMessage]:
    rows = conn.execute(
        """
        SELECT conversation_messages.id,
               conversation_messages.role,
               conversation_messages.content,
               conversation_messages.created_at
        FROM conversation_messages
        JOIN conversations
          ON conversations.thread_id = conversation_messages.thread_id
        WHERE conversation_messages.thread_id = %s
          AND conversations.user_id = %s
        ORDER BY conversation_messages.created_at ASC,
                 conversation_messages.id ASC
        LIMIT %s
        """,
        (thread_id, user_id, limit),
    ).fetchall()
    return [
        ChatMessage(id=row[0], role=row[1], content=row[2], created_at=row[3])
        for row in rows
    ]


def list_conversation_threads(
    conn: psycopg.Connection,
    user_id: str,
    limit: int = 30,
) -> list[ConversationThread]:
    rows = conn.execute(
        """
        SELECT conversations.thread_id,
               COALESCE(
                   NULLIF(
                       left(
                           min(conversation_messages.content)
                           FILTER (WHERE conversation_messages.role = 'user'),
                           80
                       ),
                       ''
                   ),
                   'New chat'
               ) AS title,
               conversations.updated_at,
               count(conversation_messages.id) AS message_count
        FROM conversations
        LEFT JOIN conversation_messages
          ON conversation_messages.thread_id = conversations.thread_id
        WHERE conversations.user_id = %s
        GROUP BY conversations.thread_id, conversations.updated_at
        ORDER BY conversations.updated_at DESC
        LIMIT %s
        """,
        (user_id, limit),
    ).fetchall()
    return [
        ConversationThread(
            thread_id=row[0],
            title=row[1],
            updated_at=row[2],
            message_count=row[3],
        )
        for row in rows
    ]


def add_message(conn: psycopg.Connection, thread_id: str, role: str, content: str) -> None:
    conn.execute(
        """
        INSERT INTO conversation_messages (thread_id, role, content)
        VALUES (%s, %s, %s)
        """,
        (thread_id, role, content),
    )


def update_user_message(
    conn: psycopg.Connection,
    thread_id: str,
    user_id: str,
    message_id: int,
    content: str,
) -> bool:
    result = conn.execute(
        """
        UPDATE conversation_messages
        SET content = %s
        FROM conversations
        WHERE conversation_messages.id = %s
          AND conversation_messages.thread_id = %s
          AND conversation_messages.role = 'user'
          AND conversations.thread_id = conversation_messages.thread_id
          AND conversations.user_id = %s
        """,
        (content, message_id, thread_id, user_id),
    )
    if result.rowcount:
        delete_following_assistant_message(conn, thread_id, user_id, message_id)
        conn.execute("UPDATE conversations SET updated_at = now() WHERE thread_id = %s", (thread_id,))
    return bool(result.rowcount)


def delete_following_assistant_message(
    conn: psycopg.Connection,
    thread_id: str,
    user_id: str,
    message_id: int,
) -> None:
    conn.execute(
        """
        DELETE FROM conversation_messages
        WHERE id = (
            SELECT assistant.id
            FROM conversation_messages AS user_message
            JOIN conversations
              ON conversations.thread_id = user_message.thread_id
            JOIN LATERAL (
                SELECT id
                FROM conversation_messages
                WHERE thread_id = user_message.thread_id
                  AND role = 'assistant'
                  AND id > user_message.id
                ORDER BY id ASC
                LIMIT 1
            ) AS assistant ON true
            WHERE user_message.id = %s
              AND user_message.thread_id = %s
              AND user_message.role = 'user'
              AND conversations.user_id = %s
        )
        """,
        (message_id, thread_id, user_id),
    )


def delete_user_turn(
    conn: psycopg.Connection,
    thread_id: str,
    user_id: str,
    message_id: int,
) -> bool:
    delete_following_assistant_message(conn, thread_id, user_id, message_id)
    result = conn.execute(
        """
        DELETE FROM conversation_messages
        USING conversations
        WHERE conversation_messages.id = %s
          AND conversation_messages.thread_id = %s
          AND conversation_messages.role = 'user'
          AND conversations.thread_id = conversation_messages.thread_id
          AND conversations.user_id = %s
        """,
        (message_id, thread_id, user_id),
    )
    if result.rowcount:
        conn.execute("UPDATE conversations SET updated_at = now() WHERE thread_id = %s", (thread_id,))
    return bool(result.rowcount)
    conn.execute(
        """
        UPDATE conversations
        SET updated_at = now()
        WHERE thread_id = %s
        """,
        (thread_id,),
    )


def search_long_memories(
    conn: psycopg.Connection,
    user_id: str,
    query_embedding: list[float],
    limit: int = LONG_MEMORY_LIMIT,
) -> list[LongMemory]:
    rows = conn.execute(
        """
        SELECT id, content, kind, embedding <=> %s::vector AS distance
        FROM long_memories
        WHERE user_id = %s
        ORDER BY distance
        LIMIT %s
        """,
        (query_embedding, user_id, limit),
    ).fetchall()
    return [
        LongMemory(id=row[0], content=row[1], kind=row[2], distance=row[3])
        for row in rows
    ]


def add_long_memory(
    conn: psycopg.Connection,
    user_id: str,
    thread_id: str,
    content: str,
    embedding: list[float],
    kind: str = "conversation_summary",
) -> None:
    conn.execute(
        """
        INSERT INTO long_memories (user_id, thread_id, kind, content, embedding, metadata)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            thread_id,
            kind,
            content,
            embedding,
            json.dumps({"source": "supportagent", "created_by": "answer_with_agent"}),
        ),
    )
