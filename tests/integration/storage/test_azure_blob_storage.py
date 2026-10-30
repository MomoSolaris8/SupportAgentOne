from uuid import uuid4

import pytest
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

from supportagent.storage.service import AzureBlobObjectStorage, get_storage

# Azurite's well-known development account. It's public and documented by Microsoft, not a secret.
AZURITE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)


@pytest.fixture
def azure_container(monkeypatch):
    """Create a fresh container in Azurite for each test and delete it afterwards."""
    name = f"test-{uuid4().hex}"
    client = BlobServiceClient.from_connection_string(AZURITE_CONNECTION_STRING)
    client.create_container(name)
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", AZURITE_CONNECTION_STRING)
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", name)
    yield client.get_container_client(name)
    client.delete_container(name)


def test_put_then_get_returns_same_bytes(azure_container):
    storage = AzureBlobObjectStorage()

    stored = storage.put_object(
        key="users/u1/a.png", content=b"png-bytes", content_type="image/png"
    )

    assert stored.provider == "azure"
    assert stored.bucket == azure_container.container_name
    assert stored.key == "users/u1/a.png"
    assert storage.get_object(bucket=stored.bucket, key=stored.key) == b"png-bytes"


def test_put_sets_content_type(azure_container):
    storage = AzureBlobObjectStorage()

    storage.put_object(key="a.png", content=b"x", content_type="image/png")

    props = azure_container.get_blob_client("a.png").get_blob_properties()
    assert props.content_settings.content_type == "image/png"


def test_put_same_key_overwrites(azure_container):
    storage = AzureBlobObjectStorage()

    storage.put_object(key="a.png", content=b"old", content_type="image/png")
    stored = storage.put_object(key="a.png", content=b"new", content_type="image/png")

    assert storage.get_object(bucket=stored.bucket, key="a.png") == b"new"


def test_get_missing_key_raises(azure_container):
    storage = AzureBlobObjectStorage()

    with pytest.raises(ResourceNotFoundError):
        storage.get_object(
            bucket=azure_container.container_name, key="does-not-exist.png"
        )


def test_get_storage_returns_azure_backend(azure_container):
    assert isinstance(get_storage("azure"), AzureBlobObjectStorage)
