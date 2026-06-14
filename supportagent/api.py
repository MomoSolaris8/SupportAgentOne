from fastapi import FastAPI
from pydantic import BaseModel

from .answer import generate_answer
from .config import load_env_file
from .retrieval import retrieve

load_env_file()

app = FastAPI(title="SupportAgent")


class AskRequest(BaseModel):
    question: str


class Source(BaseModel):
    id: int
    title: str
    url: str
    source: str
    distance: float


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    chunks = retrieve(request.question)
    answer = generate_answer(request.question, chunks)
    sources = [
        Source(
            id=i,
            title=chunk["metadata"]["title"],
            url=chunk["metadata"]["url"],
            source=chunk["metadata"]["source"],
            distance=chunk["distance"],
        )
        for i, chunk in enumerate(chunks, start=1)
    ]
    return AskResponse(answer=answer, sources=sources)
