from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from supportagent.db.models import Chunk


def upsert_chunk(session: Session, chunk: dict, embedding: list[float]) -> None:
    stmt = insert(Chunk).values(
        document_id=chunk["document_id"],
        chunk_index=chunk["chunk_index"],
        content=chunk["content"],
        embedding=embedding,
        metadata=chunk["metadata"],
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[Chunk.document_id, Chunk.chunk_index],
        set_={
            "content": stmt.excluded.content,
            "embedding": stmt.excluded.embedding,
            "metadata": stmt.excluded["metadata"],
        },
    )
    session.execute(stmt)


def search(
    session: Session,
    query_embedding: list[float],
    limit: int = 5,
    source_filter: str | None = None,
) -> list[dict]:
    distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")
    stmt = (
        select(
            Chunk.document_id,
            Chunk.chunk_index,
            Chunk.content,
            Chunk.metadata_,
            distance,
        )
        .order_by(distance)
        .limit(limit)
    )
    if source_filter:
        stmt = stmt.where(Chunk.metadata_["source"].astext == source_filter)
    return [
        {
            "document_id": row.document_id,
            "chunk_index": row.chunk_index,
            "content": row.content,
            "metadata": row.metadata_,
            "distance": row.distance,
        }
        for row in session.execute(stmt)
    ]
