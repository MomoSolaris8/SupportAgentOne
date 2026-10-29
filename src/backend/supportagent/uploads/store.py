from sqlalchemy import select
from sqlalchemy.orm import Session

from supportagent.db.models import UploadedFile


def create_uploaded_file(
    session: Session,
    file_id: str,
    user_id: str,
    thread_id: str | None,
    filename: str,
    content_type: str,
    storage_provider: str,
    storage_bucket: str,
    storage_key: str,
    image_summary: str,
    image_analysis: dict[str, object] | None = None,
) -> None:
    session.add(
        UploadedFile(
            id=file_id,
            user_id=user_id,
            thread_id=thread_id,
            filename=filename,
            content_type=content_type,
            storage_provider=storage_provider,
            storage_bucket=storage_bucket,
            storage_key=storage_key,
            image_summary=image_summary,
            image_analysis=image_analysis or {},
        )
    )


def fetch_uploaded_files(
    session: Session,
    user_id: str,
    image_ids: list[str],
) -> list[dict[str, str]]:
    files = session.scalars(
        select(UploadedFile)
        .where(UploadedFile.user_id == user_id, UploadedFile.id.in_(image_ids))
        .order_by(UploadedFile.created_at)
    )
    return [
        {
            "id": file.id,
            "filename": file.filename,
            "content_type": file.content_type,
            "image_summary": file.image_summary,
            "image_analysis": file.image_analysis or {},
        }
        for file in files
    ]


def fetch_uploaded_file(
    session: Session,
    user_id: str,
    image_id: str,
) -> dict[str, str] | None:
    file = session.scalar(
        select(UploadedFile).where(
            UploadedFile.user_id == user_id, UploadedFile.id == image_id
        )
    )
    if file is None:
        return None
    return {
        "id": file.id,
        "filename": file.filename,
        "content_type": file.content_type,
        "storage_provider": file.storage_provider,
        "storage_bucket": file.storage_bucket,
        "storage_key": file.storage_key
        if file.storage_key is not None
        else file.storage_path,
        "image_summary": file.image_summary,
        "image_analysis": file.image_analysis or {},
    }
