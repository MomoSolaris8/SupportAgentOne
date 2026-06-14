import os

from openai import OpenAI

# Default batch size for Alibaba Cloud Model Studio (DashScope) embedding
# models accessed via the OpenAI-compatible endpoint.
DEFAULT_BATCH_SIZE = 10


def get_embedding_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["EMBEDDING_API_KEY"],
        base_url=os.environ["EMBEDDING_BASE_URL"],
    )


def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-v3")
    dimensions = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))

    embeddings: list[list[float]] = []
    for start in range(0, len(texts), DEFAULT_BATCH_SIZE):
        batch = texts[start : start + DEFAULT_BATCH_SIZE]
        response = client.embeddings.create(model=model, input=batch, dimensions=dimensions)
        embeddings.extend(item.embedding for item in response.data)
    return embeddings
