from .embeddings import embed_texts, get_embedding_client
from .vector_store import get_connection, search

DEFAULT_LIMIT = 5


def retrieve(question: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    client = get_embedding_client()
    query_embedding = embed_texts(client, [question])[0]

    conn = get_connection()
    try:
        return search(conn, query_embedding, limit=limit)
    finally:
        conn.close()
