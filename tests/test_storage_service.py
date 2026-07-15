from supportagent.storage.service import LocalObjectStorage, S3ObjectStorage, SupabaseObjectStorage, get_storage


def test_local_object_storage_round_trip(tmp_path):
    storage = LocalObjectStorage(root=str(tmp_path))

    stored = storage.put_object("users/u1/image.png", b"image-bytes", "image/png")

    assert stored.provider == "local"
    assert stored.bucket == "local"
    assert stored.key == "users/u1/image.png"
    assert storage.get_object(stored.bucket, stored.key) == b"image-bytes"


def test_supabase_object_storage_uses_storage_rest_api(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200
        content = b"image"

        def raise_for_status(self):
            return None

    def fake_post(url, **kwargs):
        calls.append(("POST", url, kwargs))
        return FakeResponse()

    def fake_get(url, **kwargs):
        calls.append(("GET", url, kwargs))
        return FakeResponse()

    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "supportagent-uploads")
    monkeypatch.setattr("supportagent.storage.service.requests.post", fake_post)
    monkeypatch.setattr("supportagent.storage.service.requests.get", fake_get)

    storage = SupabaseObjectStorage()
    stored = storage.put_object("users/u1/image.png", b"image", "image/png")
    content = storage.get_object(stored.bucket, stored.key)

    assert stored.provider == "supabase"
    assert stored.bucket == "supportagent-uploads"
    assert content == b"image"
    assert calls[0][0] == "POST"
    assert calls[0][1] == "https://project.supabase.co/storage/v1/object/supportagent-uploads/users/u1/image.png"
    assert calls[0][2]["headers"]["Authorization"] == "Bearer service-key"
    assert calls[1][0] == "GET"


def test_s3_object_storage_uses_s3_compatible_client(monkeypatch):
    calls = []

    class FakeBody:
        def read(self):
            return b"image"

    class FakeS3Client:
        def put_object(self, **kwargs):
            calls.append(("put_object", kwargs))

        def get_object(self, **kwargs):
            calls.append(("get_object", kwargs))
            return {"Body": FakeBody()}

    class FakeBoto3:
        def client(self, *args, **kwargs):
            calls.append(("client", kwargs))
            return FakeS3Client()

    def fake_boto3_client(*args, **kwargs):
        calls.append(("client", kwargs))
        return FakeS3Client()

    monkeypatch.setenv("S3_ENDPOINT_URL", "http://minio:9000")
    monkeypatch.setenv("S3_REGION", "us-east-1")
    monkeypatch.setenv("S3_BUCKET", "supportagent-uploads")
    monkeypatch.setenv("S3_ACCESS_KEY_ID", "supportagent")
    monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setattr("supportagent.storage.service.boto3", FakeBoto3())
    monkeypatch.setattr("supportagent.storage.service.Config", lambda **kwargs: kwargs)

    storage = S3ObjectStorage()
    stored = storage.put_object("users/u1/image.png", b"image", "image/png")
    content = storage.get_object(stored.bucket, stored.key)

    assert stored.provider == "s3"
    assert stored.bucket == "supportagent-uploads"
    assert content == b"image"
    assert calls[0][0] == "client"
    assert calls[0][1]["endpoint_url"] == "http://minio:9000"
    assert calls[1] == (
        "put_object",
        {
            "Bucket": "supportagent-uploads",
            "Key": "users/u1/image.png",
            "Body": b"image",
            "ContentType": "image/png",
        },
    )
    assert calls[2][0] == "get_object"


def test_get_storage_supports_minio_alias(monkeypatch):
    monkeypatch.setenv("FILE_STORAGE_PROVIDER", "minio")
    monkeypatch.setattr("supportagent.storage.service.S3ObjectStorage", lambda: "s3-storage")

    assert get_storage() == "s3-storage"
