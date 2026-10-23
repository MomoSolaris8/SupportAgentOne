from datetime import datetime
from typing import Any

from sqlalchemy import Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from supportagent.db.base import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    __table_args__ = (
        Index("uploaded_files_user_created_idx", "user_id", text("created_at DESC")),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    thread_id: Mapped[str | None] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(Text)
    storage_provider: Mapped[str] = mapped_column(Text, server_default="local")
    storage_bucket: Mapped[str] = mapped_column(Text, server_default="local")
    storage_key: Mapped[str | None] = mapped_column(Text)
    storage_path: Mapped[str | None] = mapped_column(Text)
    image_analysis: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    image_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
