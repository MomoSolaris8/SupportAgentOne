from fastapi import HTTPException, status

from .email import build_password_reset_url, send_password_reset_email, smtp_configured
from .schemas import CreatedSession, ForgotPasswordRequest, ForgotPasswordResponse, LoginRequest, RegisterRequest, ResetPasswordRequest
from .security import (
    create_password_reset_token,
    hash_password,
    hash_password_reset_token,
    normalize_email,
    verify_password,
)
from .store import (
    auth_connection,
    create_password_reset_record,
    create_session,
    create_user,
    delete_user_sessions,
    get_user_by_email,
    get_valid_password_reset_user_id,
    mark_password_reset_token_used,
    update_user_password,
)

PASSWORD_RESET_TTL_MINUTES = 30


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


def request_password_reset(request: ForgotPasswordRequest) -> ForgotPasswordResponse:
    email = normalize_email(request.email)
    generic_message = "If an account exists for this email, a reset link has been sent."
    conn = auth_connection()
    try:
        record = get_user_by_email(conn, email)
        if record is None:
            return ForgotPasswordResponse(ok=True, message=generic_message)

        user, _ = record
        token = create_password_reset_token()
        reset_url = build_password_reset_url(token)
        create_password_reset_record(
            conn=conn,
            user=user,
            token_hash=hash_password_reset_token(token),
            ttl_minutes=PASSWORD_RESET_TTL_MINUTES,
        )
        email_sent = send_password_reset_email(email, reset_url)
        conn.commit()
        return ForgotPasswordResponse(
            ok=True,
            message=generic_message,
            reset_url=None if email_sent or smtp_configured() else reset_url,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reset_password(request: ResetPasswordRequest) -> None:
    token_hash = hash_password_reset_token(request.token)
    conn = auth_connection()
    try:
        user_id = get_valid_password_reset_user_id(conn, token_hash)
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset link is invalid or expired.",
            )

        update_user_password(conn, user_id, hash_password(request.password))
        mark_password_reset_token_used(conn, token_hash)
        delete_user_sessions(conn, user_id)
        conn.commit()
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
