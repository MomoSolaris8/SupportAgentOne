from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from .agent.workflow import answer_with_agent
from .logging_config import configure_logging

load_dotenv()
configure_logging()
app = FastAPI(title="SupportAgent")


# app = FastAPI(title="SupportAgent", debug=True)

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


class AgentTrace(BaseModel):
    route_source: str
    route_reason: str
    rewrite_changed: bool
    rewritten_query: str
    evidence_status: str
    evidence_reason: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    trace: AgentTrace


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
    trace = AgentTrace(
        route_source=result.route.source,
        route_reason=result.route.reason,
        rewrite_changed=result.rewrite.changed,
        rewritten_query=result.rewrite.rewritten_query,
        evidence_status=result.evidence.status,
        evidence_reason=result.evidence.reason,
    )
    return AskResponse(
        answer=result.answer,
        sources=sources,
        trace=trace,
    )
