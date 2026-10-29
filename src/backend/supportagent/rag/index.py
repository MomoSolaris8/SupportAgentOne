from dotenv import load_dotenv

from supportagent.db.session import SessionLocal

from .chunking import chunk_document
from .embeddings import embed_texts, get_embedding_client
from .ingest import collect_documents
from .vector_store import upsert_chunk


def main() -> None:
    load_dotenv()

    documents = collect_documents()
    chunks = [chunk for doc in documents for chunk in chunk_document(doc)]
    print(f"{len(documents)} documents -> {len(chunks)} chunks")

    client = get_embedding_client()
    embeddings = embed_texts(client, [chunk["content"] for chunk in chunks])

    with SessionLocal.begin() as session:
        for chunk, embedding in zip(chunks, embeddings):
            upsert_chunk(session, chunk, embedding)
    print(f"Stored {len(chunks)} chunks in pgvector")


if __name__ == "__main__":
    main()
