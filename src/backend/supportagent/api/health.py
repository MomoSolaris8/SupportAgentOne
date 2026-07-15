from supportagent.rag.vector_store import get_connection


def health() -> dict[str, str]:
    return {"status": "ok"}


def readiness() -> dict[str, str]:
    conn = get_connection()
    try:
        conn.execute("SELECT 1").fetchone()
    finally:
        conn.close()
    return {"status": "ready"}
