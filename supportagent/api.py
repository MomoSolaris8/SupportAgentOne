from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from .answer import generate_answer
from .config import load_env_file
from .retrieval import retrieve

load_env_file()

app = FastAPI(title="SupportAgent")


class AskRequest(BaseModel):
    question: str
    source: Literal["confluence", "jira"] | None = None


class Source(BaseModel):
    id: int
    title: str
    url: str
    source: str
    content: str
    distance: float


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    chunks = retrieve(request.question, source_filter=request.source)
    answer = generate_answer(request.question, chunks)
    sources = [
        Source(
            id=i,
            title=chunk["metadata"]["title"],
            url=chunk["metadata"]["url"],
            source=chunk["metadata"]["source"],
            content=chunk["content"],
            distance=chunk["distance"],
        )
        for i, chunk in enumerate(chunks, start=1)
    ]
    return AskResponse(answer=answer, sources=sources)
