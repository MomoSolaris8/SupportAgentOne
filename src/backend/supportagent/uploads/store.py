import psycopg
from psycopg.types.json import Json


def ensure_upload_schema() -> None:
    from supportagent.rag.vector_store import get_connection

    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                thread_id TEXT,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                storage_provider TEXT NOT NULL DEFAULT 'local',
                storage_bucket TEXT NOT NULL DEFAULT 'local',
                storage_key TEXT,
                storage_path TEXT,
                image_analysis JSONB NOT NULL DEFAULT '{}'::jsonb,
                image_summary TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute("ALTER TABLE uploaded_files ADD COLUMN IF NOT EXISTS storage_provider TEXT NOT NULL DEFAULT 'local'")
        conn.execute("ALTER TABLE uploaded_files ADD COLUMN IF NOT EXISTS storage_bucket TEXT NOT NULL DEFAULT 'local'")
        conn.execute("ALTER TABLE uploaded_files ADD COLUMN IF NOT EXISTS storage_key TEXT")
        conn.execute("ALTER TABLE uploaded_files ADD COLUMN IF NOT EXISTS storage_path TEXT")
        conn.execute("ALTER TABLE uploaded_files ADD COLUMN IF NOT EXISTS image_analysis JSONB NOT NULL DEFAULT '{}'::jsonb")
        conn.execute("ALTER TABLE uploaded_files ALTER COLUMN storage_path DROP NOT NULL")
        conn.execute(
            """
            UPDATE uploaded_files
            SET storage_key = storage_path
            WHERE storage_key IS NULL
              AND storage_path IS NOT NULL
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS uploaded_files_user_created_idx
            ON uploaded_files (user_id, created_at DESC)
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_uploaded_file(
    conn: psycopg.Connection,
    file_id: str,
    user_id: str,
    thread_id: str | None,
    filename: str,
    content_type: str,
    storage_provider: str,
    storage_bucket: str,
    storage_key: str,
    image_summary: str,
    image_analysis: dict[str, object] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO uploaded_files (
            id, user_id, thread_id, filename, content_type,
            storage_provider, storage_bucket, storage_key, image_summary, image_analysis
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            file_id,
            user_id,
            thread_id,
            filename,
            content_type,
            storage_provider,
            storage_bucket,
            storage_key,
            image_summary,
            Json(image_analysis or {}),
        ),
    )


def fetch_uploaded_files(
    conn: psycopg.Connection,
    user_id: str,
    image_ids: list[str],
) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT id, filename, content_type, image_summary, image_analysis
        FROM uploaded_files
        WHERE user_id = %s
          AND id = ANY(%s)
        ORDER BY created_at ASC
        """,
        (user_id, image_ids),
    ).fetchall()
    return [
        {
            "id": row[0],
            "filename": row[1],
            "content_type": row[2],
            "image_summary": row[3],
            "image_analysis": row[4] or {},
        }
        for row in rows
    ]


def fetch_uploaded_file(
    conn: psycopg.Connection,
    user_id: str,
    image_id: str,
) -> dict[str, str] | None:
    row = conn.execute(
        """
        SELECT id, filename, content_type, storage_provider, storage_bucket,
               COALESCE(storage_key, storage_path), image_summary, image_analysis
        FROM uploaded_files
        WHERE user_id = %s
          AND id = %s
        """,
        (user_id, image_id),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "filename": row[1],
        "content_type": row[2],
        "storage_provider": row[3],
        "storage_bucket": row[4],
        "storage_key": row[5],
        "image_summary": row[6],
        "image_analysis": row[7] or {},
    }
