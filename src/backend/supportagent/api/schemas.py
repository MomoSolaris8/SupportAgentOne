from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str
    source: Literal["confluence", "jira"] | None = None
    thread_id: str | None = None
    model: str | None = None
    image_ids: list[str] | None = None
    enabled_mcp_servers: list[str] | None = None
    enabled_skills: list[str] | None = None


class Source(BaseModel):
    id: int
    title: str
    url: str
    source: str
    content: str
    distance: float


class AgentTrace(BaseModel):
    thread_id: str | None
    short_memory_count: int
    long_memory_count: int
    route_source: str
    route_reason: str
    rewrite_changed: bool
    rewritten_query: str
    evidence_status: str
    evidence_reason: str
    mcp_tool_calls: list[dict] = Field(default_factory=list)
    mcp_error: str | None = None
    enabled_skills: list[str] = Field(default_factory=list)
    model: str
    image_count: int = 0


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    trace: AgentTrace


class ThreadMessage(BaseModel):
    id: int | None = None
    role: str
    content: str
    created_at: str


class UpdateThreadMessageRequest(BaseModel):
    content: str


class ThreadMessagesResponse(BaseModel):
    thread_id: str
    messages: list[ThreadMessage]


class ConversationThread(BaseModel):
    thread_id: str
    title: str
    updated_at: str
    message_count: int


class ConversationThreadsResponse(BaseModel):
    threads: list[ConversationThread]
