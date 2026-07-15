import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import requests

try:
    import boto3
    from botocore.client import Config
except ImportError:  # pragma: no cover - exercised when optional S3 dependency is absent.
    boto3 = None
    Config = None


@dataclass(frozen=True)
class StoredObject:
    provider: str
    bucket: str
    key: str


class ObjectStorage:
    provider = "base"

    def put_object(self, key: str, content: bytes, content_type: str) -> StoredObject:
        raise NotImplementedError

    def get_object(self, bucket: str, key: str) -> bytes:
        raise NotImplementedError


class LocalObjectStorage(ObjectStorage):
    provider = "local"

    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or os.environ.get("UPLOAD_STORAGE_DIR", "data/uploads")).resolve()
        self.bucket = os.environ.get("LOCAL_STORAGE_BUCKET", "local")

    def put_object(self, key: str, content: bytes, content_type: str) -> StoredObject:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return StoredObject(provider=self.provider, bucket=self.bucket, key=key)

    def get_object(self, bucket: str, key: str) -> bytes:
        return (self.root / key).read_bytes()


class SupabaseObjectStorage(ObjectStorage):
    provider = "supabase"

    def __init__(self) -> None:
        self.supabase_url = os.environ["SUPABASE_URL"].rstrip("/")
        self.service_role_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        self.bucket = os.environ.get("SUPABASE_STORAGE_BUCKET", "supportagent-uploads")

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _object_url(self, bucket: str, key: str) -> str:
        encoded_key = quote(key, safe="/")
        return f"{self.supabase_url}/storage/v1/object/{bucket}/{encoded_key}"

    def put_object(self, key: str, content: bytes, content_type: str) -> StoredObject:
        response = requests.post(
            self._object_url(self.bucket, key),
            data=content,
            headers={**self._headers(content_type), "x-upsert": "false"},
            timeout=30,
        )
        if response.status_code == 409:
            response = requests.put(
                self._object_url(self.bucket, key),
                data=content,
                headers={**self._headers(content_type), "x-upsert": "true"},
                timeout=30,
            )
        response.raise_for_status()
        return StoredObject(provider=self.provider, bucket=self.bucket, key=key)

    def get_object(self, bucket: str, key: str) -> bytes:
        response = requests.get(
            self._object_url(bucket, key),
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.content


class S3ObjectStorage(ObjectStorage):
    provider = "s3"

    def __init__(self) -> None:
        if boto3 is None or Config is None:
            raise RuntimeError("S3 storage requires the optional boto3 dependency.")
        self.bucket = os.environ.get("S3_BUCKET", "supportagent-uploads")
        endpoint_url = os.environ.get("S3_ENDPOINT_URL")
        region_name = os.environ.get("S3_REGION", "us-east-1")
        access_key_id = os.environ.get("S3_ACCESS_KEY_ID")
        secret_access_key = os.environ.get("S3_SECRET_ACCESS_KEY")
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(signature_version="s3v4"),
        )

    def put_object(self, key: str, content: bytes, content_type: str) -> StoredObject:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return StoredObject(provider=self.provider, bucket=self.bucket, key=key)

    def get_object(self, bucket: str, key: str) -> bytes:
        response = self.client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()


def get_storage(provider: str | None = None) -> ObjectStorage:
    provider = (provider or os.environ.get("FILE_STORAGE_PROVIDER", "local")).lower()
    if provider == "supabase":
        return SupabaseObjectStorage()
    if provider in {"s3", "minio"}:
        return S3ObjectStorage()
    if provider == "local":
        return LocalObjectStorage()
    raise ValueError(f"Unsupported FILE_STORAGE_PROVIDER: {provider}")
