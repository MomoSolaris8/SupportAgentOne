from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from supportagent.db.models import PasswordResetToken, User, UserSession
from supportagent.db.session import SessionLocal

from .schemas import AuthUser, CreatedSession
from .security import create_session_token, hash_session_token, session_ttl_days


def _to_auth_user(user: User) -> AuthUser:
    return AuthUser(id=user.id, email=user.email, display_name=user.display_name)


def get_user_by_email(session: Session, email: str) -> tuple[AuthUser, str] | None:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        return None
    return _to_auth_user(user), user.password_hash


def get_user_by_id(session: Session, user_id: str) -> AuthUser | None:
    user = session.get(User, user_id)
    return _to_auth_user(user) if user else None


def create_user(
    session: Session,
    email: str,
    password_hash: str,
    display_name: str | None,
) -> AuthUser:
    user = User(
        id=str(uuid4()),
        email=email,
        display_name=display_name,
        password_hash=password_hash,
    )
    session.add(user)
    session.flush()
    return _to_auth_user(user)


def create_session(session: Session, user: AuthUser) -> CreatedSession:
    token = create_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=session_ttl_days())
    session.add(
        UserSession(
            id=str(uuid4()),
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=expires_at,
        )
    )
    return CreatedSession(token=token, expires_at=expires_at, user=user)


def create_password_reset_record(
    session: Session,
    user: AuthUser,
    token_hash: str,
    ttl_minutes: int,
) -> None:
    session.add(
        PasswordResetToken(
            id=str(uuid4()),
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
        )
    )


def get_valid_password_reset_user_id(session: Session, token_hash: str) -> str | None:
    return session.scalar(
        select(PasswordResetToken.user_id).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > func.now(),
        )
    )


def mark_password_reset_token_used(session: Session, token_hash: str) -> None:
    session.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .values(used_at=func.now())
    )


def update_user_password(session: Session, user_id: str, password_hash: str) -> None:
    session.execute(
        update(User)
        .where(User.id == user_id)
        .values(password_hash=password_hash, updated_at=func.now())
    )


def delete_user_sessions(session: Session, user_id: str) -> None:
    session.execute(delete(UserSession).where(UserSession.user_id == user_id))


def get_user_by_session_token(token: str) -> AuthUser | None:
    with SessionLocal() as session:
        user = session.scalar(
            select(User)
            .join(UserSession, UserSession.user_id == User.id)
            .where(
                UserSession.token_hash == hash_session_token(token),
                UserSession.expires_at > func.now(),
            )
        )
        return _to_auth_user(user) if user else None


def delete_session_token(token: str) -> None:
    with SessionLocal.begin() as session:
        session.execute(
            delete(UserSession).where(
                UserSession.token_hash == hash_session_token(token)
            )
        )
