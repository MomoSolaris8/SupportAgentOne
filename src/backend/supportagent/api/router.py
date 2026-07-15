from fastapi import FastAPI

from supportagent.api.ask import ask
from supportagent.api.health import health, readiness
from supportagent.api.mcp import (
    McpAuditResponse,
    McpServersResponse,
    McpToolCallResponse,
    McpToolsResponse,
    mcp_audit,
    mcp_call,
    mcp_credentials,
    mcp_server_upsert,
    mcp_servers,
    mcp_tools,
)
from supportagent.api.models import ChatModelsResponse, chat_models
from supportagent.api.schemas import AskResponse, ConversationThreadsResponse, ThreadMessagesResponse
from supportagent.api.skills import SkillsResponse, skills
from supportagent.api.threads import delete_thread_message, thread_messages, threads, update_thread_message
from supportagent.api.uploads import UploadedImageResponse, preview_image, upload_image
from supportagent.auth.microsoft import microsoft_callback, microsoft_start
from supportagent.auth.router import login, logout, me, register
from supportagent.auth.schemas import UserPublic


def register_routes(app: FastAPI) -> None:
    app.add_api_route("/health", health, methods=["GET"], tags=["Health"])
    app.add_api_route("/ready", readiness, methods=["GET"], tags=["Health"])
    app.add_api_route("/auth/register", register, methods=["POST"], response_model=UserPublic, tags=["Auth"])
    app.add_api_route("/auth/login", login, methods=["POST"], response_model=UserPublic, tags=["Auth"])
    app.add_api_route("/auth/me", me, methods=["GET"], response_model=UserPublic, tags=["Auth"])
    app.add_api_route("/auth/logout", logout, methods=["POST"], tags=["Auth"])
    app.add_api_route("/auth/microsoft/start", microsoft_start, methods=["GET"], tags=["Auth"])
    app.add_api_route("/auth/microsoft/callback", microsoft_callback, methods=["GET"], tags=["Auth"])
    app.add_api_route("/ask", ask, methods=["POST"], response_model=AskResponse, tags=["Ask"])
    app.add_api_route("/uploads/image", upload_image, methods=["POST"], response_model=UploadedImageResponse, tags=["Uploads"])
    app.add_api_route("/uploads/image/{image_id}", preview_image, methods=["GET"], tags=["Uploads"])
    app.add_api_route("/models", chat_models, methods=["GET"], response_model=ChatModelsResponse, tags=["Models"])
    app.add_api_route("/skills", skills, methods=["GET"], response_model=SkillsResponse, tags=["Skills"])
    app.add_api_route("/mcp/tools", mcp_tools, methods=["GET"], response_model=McpToolsResponse, tags=["MCP"])
    app.add_api_route("/mcp/servers", mcp_servers, methods=["GET"], response_model=McpServersResponse, tags=["MCP"])
    app.add_api_route("/mcp/servers", mcp_server_upsert, methods=["POST"], tags=["MCP"])
    app.add_api_route("/mcp/credentials", mcp_credentials, methods=["POST"], tags=["MCP"])
    app.add_api_route("/mcp/audit", mcp_audit, methods=["GET"], response_model=McpAuditResponse, tags=["MCP"])
    app.add_api_route("/mcp/call", mcp_call, methods=["POST"], response_model=McpToolCallResponse, tags=["MCP"])
    app.add_api_route("/threads", threads, methods=["GET"], response_model=ConversationThreadsResponse, tags=["Threads"])
    app.add_api_route(
        "/threads/{thread_id}/messages",
        thread_messages,
        methods=["GET"],
        response_model=ThreadMessagesResponse,
        tags=["Threads"],
    )
    app.add_api_route(
        "/threads/{thread_id}/messages/{message_id}",
        update_thread_message,
        methods=["PATCH"],
        response_model=ThreadMessagesResponse,
        tags=["Threads"],
    )
    app.add_api_route(
        "/threads/{thread_id}/messages/{message_id}",
        delete_thread_message,
        methods=["DELETE"],
        response_model=ThreadMessagesResponse,
        tags=["Threads"],
    )
