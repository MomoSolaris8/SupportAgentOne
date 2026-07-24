from fastapi import APIRouter, Depends, HTTPException

from supportagent.agent.workflow import answer_with_agent
from supportagent.api.schemas import AgentTrace, AskRequest, AskResponse, Source
from supportagent.auth.dependencies import get_current_user
from supportagent.auth.schemas import AuthUser
from supportagent.llm import ModelConfigurationError
from supportagent.uploads import get_image_contexts

router = APIRouter(tags=["Ask"])


@router.post("/ask", response_model=AskResponse)
def ask(
    request: AskRequest,
    user: AuthUser = Depends(get_current_user),
) -> AskResponse:
    image_contexts = get_image_contexts(user.id, request.image_ids)
    try:
        result = answer_with_agent(
            request.question,
            source_filter=request.source,
            thread_id=request.thread_id,
            user_id=user.id,
            requested_model=request.model,
            image_contexts=image_contexts,
            enabled_mcp_servers=request.enabled_mcp_servers,
            enabled_skills=request.enabled_skills,
        )
    except ModelConfigurationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
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
        thread_id=request.thread_id,
        short_memory_count=result.short_memory_count,
        long_memory_count=result.long_memory_count,
        route_source=result.route.source,
        route_reason=result.route.reason,
        rewrite_changed=result.rewrite.changed,
        rewritten_query=result.rewrite.rewritten_query,
        evidence_status=result.evidence.status,
        evidence_reason=result.evidence.reason,
        mcp_tool_calls=[
            {
                "server": tool_call.server,
                "tool": tool_call.tool,
                "arguments": tool_call.arguments,
                "result_preview": tool_call.result_preview,
            }
            for tool_call in result.mcp_tool_calls or []
        ],
        mcp_error=result.mcp_error,
        enabled_skills=result.enabled_skills,
        model=result.model,
        image_count=result.image_count,
    )
    return AskResponse(
        answer=result.answer,
        sources=sources,
        trace=trace,
    )
