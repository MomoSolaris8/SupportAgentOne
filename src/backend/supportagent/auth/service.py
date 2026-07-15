from fastapi import HTTPException, status

from .schemas import CreatedSession, LoginRequest, RegisterRequest
from .security import hash_password, normalize_email, verify_password
from .store import auth_connection, create_session, create_user, get_user_by_email


def register_user(request: RegisterRequest) -> CreatedSession:
    email = normalize_email(request.email)
    display_name = request.display_name.strip() if request.display_name else None

    conn = auth_connection()
    try:
        if get_user_by_email(conn, email) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

        user = create_user(
            conn=conn,
            email=email,
            password_hash=hash_password(request.password),
            display_name=display_name,
        )
        session = create_session(conn, user)
        conn.commit()
        return session
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def login_user(request: LoginRequest) -> CreatedSession:
    email = normalize_email(request.email)
    conn = auth_connection()
    try:
        record = get_user_by_email(conn, email)
        if record is None:
            raise_invalid_login()

        user, stored_hash = record
        if not verify_password(request.password, stored_hash):
            raise_invalid_login()

        session = create_session(conn, user)
        conn.commit()
        return session
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def raise_invalid_login() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
    )
