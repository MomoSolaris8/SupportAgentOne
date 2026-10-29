from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from supportagent.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from supportagent.auth.service import (
    login_user,
    register_user,
    request_password_reset,
    reset_password,
)
from supportagent.auth.store import delete_session_token, get_user_by_session_token
from supportagent.db.session import engine


@pytest.fixture(autouse=True)
def _no_smtp(clean_db, monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)


def _register(
    email="Ada@Example.com ", password="correct-horse", display_name="  Ada  "
):
    return register_user(
        RegisterRequest(email=email, password=password, display_name=display_name)
    )


def _reset_token() -> str:
    response = request_password_reset(ForgotPasswordRequest(email="ada@example.com"))
    return parse_qs(urlparse(response.reset_url).query)["reset_token"][0]


def test_register_creates_user_and_logged_in_session():
    session = _register()

    user = get_user_by_session_token(session.token)

    assert user is not None
    assert user.email == "ada@example.com"
    assert user.display_name == "Ada"
    assert user.id == session.user.id


def test_register_rejects_duplicate_email_case_insensitively():
    _register()

    with pytest.raises(HTTPException) as error:
        _register(email="ADA@example.com")

    assert error.value.status_code == 409


def test_login_returns_new_session_for_correct_password():
    registered = _register()

    session = login_user(
        LoginRequest(email="ada@example.com", password="correct-horse")
    )

    assert session.token != registered.token
    assert get_user_by_session_token(session.token).id == registered.user.id


@pytest.mark.parametrize(
    ("email", "password"),
    [("ada@example.com", "wrong-password"), ("nobody@example.com", "correct-horse")],
)
def test_login_rejects_bad_credentials(email, password):
    _register()

    with pytest.raises(HTTPException) as error:
        login_user(LoginRequest(email=email, password=password))

    assert error.value.status_code == 401


def test_logout_invalidates_session():
    session = _register()

    delete_session_token(session.token)

    assert get_user_by_session_token(session.token) is None


def test_expired_session_is_rejected():
    session = _register()
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE user_sessions SET expires_at = now() - interval '1 minute'")
        )

    assert get_user_by_session_token(session.token) is None


def test_password_reset_changes_password_and_revokes_sessions():
    old_session = _register()

    reset_password(
        ResetPasswordRequest(token=_reset_token(), password="new-password-1")
    )

    assert get_user_by_session_token(old_session.token) is None
    with pytest.raises(HTTPException):
        login_user(LoginRequest(email="ada@example.com", password="correct-horse"))
    assert login_user(LoginRequest(email="ada@example.com", password="new-password-1"))


def test_password_reset_token_can_only_be_used_once():
    _register()
    token = _reset_token()
    reset_password(ResetPasswordRequest(token=token, password="new-password-1"))

    with pytest.raises(HTTPException) as error:
        reset_password(ResetPasswordRequest(token=token, password="new-password-2"))

    assert error.value.status_code == 400


def test_expired_password_reset_token_is_rejected():
    _register()
    token = _reset_token()
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE password_reset_tokens SET expires_at = now() - interval '1 minute'"
            )
        )

    with pytest.raises(HTTPException) as error:
        reset_password(ResetPasswordRequest(token=token, password="new-password-1"))

    assert error.value.status_code == 400


def test_password_reset_request_for_unknown_email_reveals_nothing():
    _register()

    unknown = request_password_reset(ForgotPasswordRequest(email="nobody@example.com"))
    known = request_password_reset(ForgotPasswordRequest(email="ada@example.com"))

    assert unknown.reset_url is None
    assert unknown.message == known.message
