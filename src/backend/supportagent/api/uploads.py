from fastapi import Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from supportagent.auth.dependencies import get_current_user
from supportagent.auth.schemas import AuthUser
from supportagent.rag.vector_store import get_connection
from supportagent.storage import get_storage
from supportagent.uploads import save_uploaded_image
from supportagent.uploads.store import fetch_uploaded_file


class UploadedImageResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    image_summary: str
    preview_url: str


async def upload_image(
    file: UploadFile = File(...),
    thread_id: str | None = Form(default=None),
    user: AuthUser = Depends(get_current_user),
) -> UploadedImageResponse:
    try:
        uploaded = await save_uploaded_image(file, user_id=user.id, thread_id=thread_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {error}") from error
    return UploadedImageResponse(
        id=uploaded.id,
        filename=uploaded.filename,
        content_type=uploaded.content_type,
        image_summary=uploaded.image_summary,
        preview_url=uploaded.preview_url,
    )


def preview_image(
    image_id: str,
    user: AuthUser = Depends(get_current_user),
) -> Response:
    conn = get_connection()
    try:
        record = fetch_uploaded_file(conn, user_id=user.id, image_id=image_id)
    finally:
        conn.close()
    if record is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    try:
        content = get_storage(record["storage_provider"]).get_object(
            bucket=record["storage_bucket"],
            key=record["storage_key"],
        )
    except Exception as error:
        raise HTTPException(status_code=404, detail="Image content not found.") from error
    return Response(
        content=content,
        media_type=record["content_type"],
        headers={"Content-Disposition": f'inline; filename="{record["filename"]}"'},
    )
