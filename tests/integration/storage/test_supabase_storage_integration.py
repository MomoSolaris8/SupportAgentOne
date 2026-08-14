import base64
import os
from uuid import uuid4

import pytest
import requests

from supportagent.storage.service import SupabaseObjectStorage


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@pytest.fixture
def supabase_storage_object():
    """Provide a unique object key and remove it after the integration test."""

    required = ["SUPABASE_URL", "SUPABASE_STORAGE_BUCKET"]
    missing = [name for name in required if not os.environ.get(name)]
    has_secret = bool(
        os.environ.get("SUPABASE_SECRET_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    )

    if missing or not has_secret:
        missing_names = [*missing]
        if not has_secret:
            missing_names.append("SUPABASE_SECRET_KEY")
        pytest.fail(
            "Missing Supabase integration environment: "
            + ", ".join(missing_names)
            + ". Load .env.azure.local before running integration tests."
        )

    storage = SupabaseObjectStorage()
    key = f"integration-tests/{uuid4()}.png"

    try:
        yield storage, key
    finally:
        response = requests.delete(
            f"{storage.supabase_url}/storage/v1/object/{storage.bucket}",
            json={"prefixes": [key]},
            headers=storage._headers(),
            timeout=30,
        )
        response.raise_for_status()


def test_supabase_storage_upload_download_round_trip(supabase_storage_object):
    storage, key = supabase_storage_object

    stored = storage.put_object(key, PNG_BYTES, "image/png")
    downloaded = storage.get_object(stored.bucket, stored.key)

    assert stored.provider == "supabase"
    assert stored.bucket == os.environ["SUPABASE_STORAGE_BUCKET"]
    assert stored.key == key
    assert downloaded == PNG_BYTES
