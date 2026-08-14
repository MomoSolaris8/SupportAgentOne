from supportagent.auth.security import (
    create_session_token,
    hash_password,
    hash_session_token,
    normalize_email,
    verify_password,
)


def test_password_hash_round_trip():
    stored_hash = hash_password("password123")

    assert stored_hash != "password123"
    assert verify_password("password123", stored_hash) is True
    assert verify_password("wrong-password", stored_hash) is False


def test_session_token_hash_is_stable_without_storing_plaintext():
    token = create_session_token()
    token_hash = hash_session_token(token)

    assert token_hash == hash_session_token(token)
    assert token_hash != token


def test_normalize_email():
    assert normalize_email("  Momo@Example.COM ") == "momo@example.com"
