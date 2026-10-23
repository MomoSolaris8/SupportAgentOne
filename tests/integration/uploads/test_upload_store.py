import pytest

from supportagent.rag.vector_store import get_connection
from supportagent.uploads.store import (
    create_uploaded_file,
    fetch_uploaded_file,
    fetch_uploaded_files,
)


@pytest.fixture
def conn(clean_db):
    conn = get_connection()
    yield conn
    conn.rollback()
    conn.close()


def _create(conn, file_id, user_id="user-1", **overrides):
    values = {
        "file_id": file_id,
        "user_id": user_id,
        "thread_id": "thread-1",
        "filename": f"{file_id}.png",
        "content_type": "image/png",
        "storage_provider": "local",
        "storage_bucket": "local",
        "storage_key": f"users/{user_id}/{file_id}.png",
        "image_summary": "a damaged bumper",
        "image_analysis": {"ocr_text": "INVOICE 42"},
    }
    values.update(overrides)
    create_uploaded_file(conn, **values)


def test_fetch_uploaded_file_returns_stored_record(conn):
    _create(conn, "img-1")

    record = fetch_uploaded_file(conn, user_id="user-1", image_id="img-1")

    assert record == {
        "id": "img-1",
        "filename": "img-1.png",
        "content_type": "image/png",
        "storage_provider": "local",
        "storage_bucket": "local",
        "storage_key": "users/user-1/img-1.png",
        "image_summary": "a damaged bumper",
        "image_analysis": {"ocr_text": "INVOICE 42"},
    }


def test_fetch_uploaded_file_hides_other_users_files(conn):
    _create(conn, "img-1", user_id="owner")

    assert fetch_uploaded_file(conn, user_id="someone-else", image_id="img-1") is None


def test_missing_image_analysis_is_stored_as_empty_object(conn):
    _create(conn, "img-1", image_analysis=None)

    record = fetch_uploaded_file(conn, user_id="user-1", image_id="img-1")

    assert record["image_analysis"] == {}


def test_legacy_rows_fall_back_to_storage_path(conn):
    conn.execute(
        """
        INSERT INTO uploaded_files
            (id, user_id, filename, content_type, storage_path, image_summary)
        VALUES ('legacy', 'user-1', 'old.png', 'image/png', '/data/old.png', 'old')
        """
    )

    record = fetch_uploaded_file(conn, user_id="user-1", image_id="legacy")

    assert record["storage_key"] == "/data/old.png"


def test_fetch_uploaded_files_filters_by_user_and_orders_by_upload_time(conn):
    _create(conn, "newer")
    _create(conn, "older")
    _create(conn, "foreign", user_id="user-2")
    conn.execute(
        "UPDATE uploaded_files SET created_at = now() - interval '1 hour' WHERE id = 'older'"
    )

    rows = fetch_uploaded_files(
        conn, user_id="user-1", image_ids=["newer", "older", "foreign", "missing"]
    )

    assert [row["id"] for row in rows] == ["older", "newer"]
