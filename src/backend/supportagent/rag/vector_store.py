import json
import os

import psycopg
from pgvector.psycopg import register_vector


def get_connection() -> psycopg.Connection:
    conn = psycopg.connect(
        os.environ["DATABASE_URL"],
        prepare_threshold=None,
        connect_timeout=int(os.environ.get("DATABASE_CONNECT_TIMEOUT_SECONDS", "5")),
    )
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    register_vector(conn)
    return conn


def create_schema(conn: psycopg.Connection, dimensions: int) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS chunks (
            id SERIAL PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_index INT NOT NULL,
            content TEXT NOT NULL,
            embedding vector({dimensions}),
            metadata JSONB NOT NULL,
            UNIQUE (document_id, chunk_index)
        )
        """
    )
    conn.commit()


def upsert_chunk(conn: psycopg.Connection, chunk: dict, embedding: list[float]) -> None:
    conn.execute(
        """
        INSERT INTO chunks (document_id, chunk_index, content, embedding, metadata)
        VALUES (%(document_id)s, %(chunk_index)s, %(content)s, %(embedding)s, %(metadata)s)
        ON CONFLICT (document_id, chunk_index)
        DO UPDATE SET
            content = EXCLUDED.content,
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata
        """,
        {
            "document_id": chunk["document_id"],
            "chunk_index": chunk["chunk_index"],
            "content": chunk["content"],
            "embedding": embedding,
            "metadata": json.dumps(chunk["metadata"], ensure_ascii=False),
        },
    )


def search(
    conn: psycopg.Connection,
    query_embedding: list[float],
    limit: int = 5,
    source_filter: str | None = None,
) -> list[dict]:
    where_clause = "WHERE metadata->>'source' = %s" if source_filter else ""
    params: list = [query_embedding]
    if source_filter:
        params.append(source_filter)
    params.append(limit)

    rows = conn.execute(
        f"""
        SELECT document_id, chunk_index, content, metadata, embedding <=> %s::vector AS distance
        FROM chunks
        {where_clause}
        ORDER BY distance
        LIMIT %s
        """,
        params,
    ).fetchall()
    return [
        {
            "document_id": row[0],
            "chunk_index": row[1],
            "content": row[2],
            "metadata": row[3],
            "distance": row[4],
        }
        for row in rows
    ]
