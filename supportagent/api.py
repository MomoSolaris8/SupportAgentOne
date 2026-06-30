from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from .agent.workflow import answer_with_agent
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="SupportAgent")
#app = FastAPI(title="SupportAgent", debug=True)

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
    result = answer_with_agent(
        request.question,
        source_filter=request.source,
    )
    sources = [
        Source(
            id=i,
            title=chunk["metadata"]["title"],
            url=chunk["metadata"]["url"],
            source=chunk["metadata"]["source"],
            content=chunk["content"],
            distance=chunk["distance"],
        )
        for i, chunk in enumerate(result.chunks, start=1)
    ]
    return AskResponse(answer=result.answer, sources=sources)
