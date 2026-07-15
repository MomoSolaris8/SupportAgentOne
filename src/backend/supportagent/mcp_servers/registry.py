import inspect
from typing import Any

from pydantic.fields import FieldInfo

from supportagent.mcp_servers.teams_mcp.tools import TEAMS_TOOLS
from supportagent.mcp_servers.weather_mcp.tools import WEATHER_TOOLS


TOOL_REGISTRY = {
    "teams_mcp": {tool.__name__: tool for tool in TEAMS_TOOLS},
    "weather_mcp": {tool.__name__: tool for tool in WEATHER_TOOLS},
}


EXAMPLE_ARGUMENTS: dict[tuple[str, str], dict[str, Any]] = {
    ("teams_mcp", "batch_get_user_info"): {"emails": ["yuheydemann@outlook.de"]},
    ("teams_mcp", "get_calendars_list"): {"user_id": "yuheydemann@outlook.de"},
    ("teams_mcp", "create_calendar"): {"user_id": "yuheydemann@outlook.de", "name": "Interview Prep"},
    ("teams_mcp", "create_calendar_event"): {
        "user_id": "yuheydemann@outlook.de",
        "calendar_id": "primary",
        "subject": "Mock interview",
        "start_time": "2026-07-14T09:00:00",
        "end_time": "2026-07-14T10:00:00",
        "timezone": "W. Europe Standard Time",
    },
    ("teams_mcp", "create_document"): {
        "user_id": "yuheydemann@outlook.de",
        "name": "interview-notes.txt",
        "content": "Notes from SupportAgent.",
    },
    ("teams_mcp", "create_message"): {"chat_id": "replace-with-chat-id", "content": "Hello from SupportAgent."},
    ("weather_mcp", "get_weather"): {"location": "Zurich", "days": 3},
}


def _annotation_name(annotation: Any) -> str:
    if annotation is inspect.Signature.empty:
        return "any"
    return str(annotation).replace("typing.", "")


def _field_default(default: Any) -> tuple[bool, Any, str | None]:
    if isinstance(default, FieldInfo):
        required = default.is_required()
        value = None if required else default.default
        description = default.description
        return required, value, description
    if default is inspect.Signature.empty:
        return True, None, None
    return False, default, None


def describe_tool(server: str, name: str, tool: Any) -> dict[str, Any]:
    signature = inspect.signature(tool)
    parameters = []
    for param_name, parameter in signature.parameters.items():
        required, default, description = _field_default(parameter.default)
        if param_name == "access_token" or param_name == "api_key":
            required = False
            default = None
        parameters.append(
            {
                "name": param_name,
                "type": _annotation_name(parameter.annotation),
                "required": required,
                "default": default,
                "description": description,
            }
        )
    return {
        "server": server,
        "name": name,
        "description": inspect.getdoc(tool) or "",
        "parameters": parameters,
        "example_arguments": EXAMPLE_ARGUMENTS.get((server, name), {}),
    }


def list_tools() -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for server, server_tools in TOOL_REGISTRY.items():
        tools.extend(describe_tool(server, name, tool) for name, tool in server_tools.items())
    return tools


def get_tool(server: str, name: str) -> Any | None:
    return TOOL_REGISTRY.get(server, {}).get(name)
