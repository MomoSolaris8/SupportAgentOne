import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from supportagent.rag.vector_store import get_connection
from supportagent.storage import get_storage
from supportagent.uploads.store import create_uploaded_file, ensure_upload_schema, fetch_uploaded_files
from supportagent.vision.service import analyze_image

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class UploadedImage:
    id: str
    filename: str
    content_type: str
    image_summary: str
    preview_url: str


def upload_root() -> Path:
    return Path(os.environ.get("UPLOAD_STORAGE_DIR", "data/uploads")).resolve()


def _extension(filename: str, content_type: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return suffix
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(content_type, ".img")


async def save_uploaded_image(
    upload: UploadFile,
    user_id: str,
    thread_id: str | None = None,
) -> UploadedImage:
    content_type = upload.content_type or "application/octet-stream"
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError("Only JPEG, PNG, WEBP, and GIF images are supported.")

    content = await upload.read()
    if not content:
        raise ValueError("Uploaded image is empty.")
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError("Uploaded image is too large. Maximum size is 8 MB.")

    image_id = str(uuid.uuid4())
    filename = upload.filename or "image"
    storage_key = f"users/{user_id}/{image_id}{_extension(filename, content_type)}"
    stored = get_storage().put_object(
        key=storage_key,
        content=content,
        content_type=content_type,
    )

    image_analysis = analyze_image(
        image_bytes=content,
        content_type=content_type,
        filename=filename,
    )
    image_summary = image_analysis.summary(filename)

    ensure_upload_schema()
    conn = get_connection()
    try:
        create_uploaded_file(
            conn,
            file_id=image_id,
            user_id=user_id,
            thread_id=thread_id,
            filename=filename,
            content_type=content_type,
            storage_provider=stored.provider,
            storage_bucket=stored.bucket,
            storage_key=stored.key,
            image_summary=image_summary,
            image_analysis=image_analysis.to_dict(),
        )
        conn.commit()
    finally:
        conn.close()

    return UploadedImage(
        id=image_id,
        filename=filename,
        content_type=content_type,
        image_summary=image_summary,
        preview_url=f"/uploads/image/{image_id}",
    )


def get_image_contexts(user_id: str, image_ids: list[str] | None) -> list[str]:
    if not image_ids:
        return []

    conn = get_connection()
    try:
        rows = fetch_uploaded_files(conn, user_id=user_id, image_ids=image_ids)
    finally:
        conn.close()

    contexts = []
    for row in rows:
        analysis = row.get("image_analysis") or {}
        contexts.append(
            "\n".join(
                [
                    f"Image id: {row['id']}",
                    f"Filename: {row['filename']}",
                    f"Content type: {row['content_type']}",
                    f"OCR text: {analysis.get('ocr_text') or ''}",
                    f"Visible objects: {_join_analysis_items(analysis.get('visible_objects'))}",
                    f"Dates: {_join_analysis_items(analysis.get('dates'))}",
                    f"Amounts: {_join_analysis_items(analysis.get('amounts'))}",
                    f"Names/organizations/places: {_join_analysis_items(analysis.get('names'))}",
                    f"Insurance relevant facts: {_join_analysis_items(analysis.get('insurance_relevant_facts'))}",
                    f"Limitations: {analysis.get('limitations') or ''}",
                    f"Legacy observation: {row['image_summary']}",
                ]
            )
        )
    return contexts


def _join_analysis_items(value: object) -> str:
    if not isinstance(value, list):
        return ""
    return "; ".join(str(item) for item in value if str(item).strip())
