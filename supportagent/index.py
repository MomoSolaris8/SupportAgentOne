import os

from .chunking import chunk_document
from .config import load_env_file
from .embeddings import embed_texts, get_embedding_client
from .ingest import collect_documents
from .vector_store import create_schema, get_connection, upsert_chunk


def main() -> None:
    load_env_file()

    documents = collect_documents()
    chunks = [chunk for doc in documents for chunk in chunk_document(doc)]
    print(f"{len(documents)} documents -> {len(chunks)} chunks")

    client = get_embedding_client()
    embeddings = embed_texts(client, [chunk["content"] for chunk in chunks])

    dimensions = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))
    conn = get_connection()
    create_schema(conn, dimensions)
    for chunk, embedding in zip(chunks, embeddings):
        upsert_chunk(conn, chunk, embedding)
    conn.commit()
    print(f"Stored {len(chunks)} chunks in pgvector")


if __name__ == "__main__":
    main()
