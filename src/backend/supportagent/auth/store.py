from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from supportagent.rag.vector_store import get_connection

from .schemas import AuthUser, CreatedSession
from .security import create_session_token, hash_session_token, session_ttl_days


def create_auth_schema(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            display_name TEXT,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash TEXT UNIQUE NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS user_sessions_token_hash_idx
        ON user_sessions (token_hash)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS user_sessions_user_expires_idx
        ON user_sessions (user_id, expires_at DESC)
        """
    )
    conn.commit()


def auth_connection() -> psycopg.Connection:
    conn = get_connection()
    create_auth_schema(conn)
    return conn


def row_to_user(row: dict) -> AuthUser:
    return AuthUser(
        id=row["id"],
        email=row["email"],
        display_name=row["display_name"],
    )


def get_user_by_email(conn: psycopg.Connection, email: str) -> tuple[AuthUser, str] | None:
    row = conn.execute(
        """
        SELECT id, email, display_name, password_hash
        FROM users
        WHERE email = %s
        """,
        (email,),
        prepare=False,
    ).fetchone()
    if row is None:
        return None
    user = AuthUser(id=row[0], email=row[1], display_name=row[2])
    return user, row[3]


def create_user(
    conn: psycopg.Connection,
    email: str,
    password_hash: str,
    display_name: str | None,
) -> AuthUser:
    user_id = str(uuid4())
    row = conn.execute(
        """
        INSERT INTO users (id, email, display_name, password_hash)
        VALUES (%s, %s, %s, %s)
        RETURNING id, email, display_name
        """,
        (user_id, email, display_name, password_hash),
    ).fetchone()
    return AuthUser(id=row[0], email=row[1], display_name=row[2])


def create_session(conn: psycopg.Connection, user: AuthUser) -> CreatedSession:
    token = create_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=session_ttl_days())
    conn.execute(
        """
        INSERT INTO user_sessions (id, user_id, token_hash, expires_at)
        VALUES (%s, %s, %s, %s)
        """,
        (str(uuid4()), user.id, hash_session_token(token), expires_at),
    )
    return CreatedSession(token=token, expires_at=expires_at, user=user)


def get_user_by_session_token(token: str) -> AuthUser | None:
    conn = auth_connection()
    try:
        token_hash = hash_session_token(token)
        with conn.cursor(row_factory=dict_row) as cursor:
            row = cursor.execute(
                """
                SELECT users.id, users.email, users.display_name
                FROM user_sessions
                JOIN users ON users.id = user_sessions.user_id
                WHERE user_sessions.token_hash = %s
                  AND user_sessions.expires_at > now()
                """,
                (token_hash,),
            ).fetchone()
        if row is None:
            return None
        return row_to_user(row)
    finally:
        conn.close()


def delete_session_token(token: str) -> None:
    conn = auth_connection()
    try:
        conn.execute(
            "DELETE FROM user_sessions WHERE token_hash = %s",
            (hash_session_token(token),),
        )
        conn.commit()
    finally:
        conn.close()
