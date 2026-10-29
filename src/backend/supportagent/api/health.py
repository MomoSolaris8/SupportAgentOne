from sqlalchemy import text

from supportagent.db.session import engine


def health() -> dict[str, str]:
    return {"status": "ok"}


def readiness() -> dict[str, str]:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ready"}
