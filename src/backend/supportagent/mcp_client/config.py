import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from supportagent.mcp_client.store import list_mcp_servers


Transport = Literal["stdio", "sse", "streamable_http"]


@dataclass(frozen=True)
class MCPServerConfig:
    server_name: str
    transport: Transport
    command: str | None = None
    args: list[str] = field(default_factory=list)
    url: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None


READ_ONLY_TOOLS = {
    "batch_get_user_info",
    "get_calendar_info",
    "get_calendars_list",
    "get_calendar_event",
    "get_document",
    "list_folder_files",
    "list_chats",
    "get_weather",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def pythonpath_env() -> str:
    backend_path = str(project_root() / "src" / "backend")
    existing = os.environ.get("PYTHONPATH")
    return f"{backend_path}{os.pathsep}{existing}" if existing else backend_path


def _config_from_row(row: dict[str, object], base_env: dict[str, str]) -> MCPServerConfig | None:
    if not row.get("enabled"):
        return None

    server_config = row.get("config")
    if not isinstance(server_config, dict):
        server_config = {}

    transport = row["transport"]
    if transport not in {"stdio", "sse", "streamable_http"}:
        return None

    command = server_config.get("command")
    if command == "python":
        command = sys.executable

    env = dict(base_env)
    configured_env = server_config.get("env")
    if isinstance(configured_env, dict):
        env.update({str(key): str(value) for key, value in configured_env.items()})

    args = server_config.get("args")
    url = server_config.get("url")
    cwd = server_config.get("cwd")

    return MCPServerConfig(
        server_name=str(row["server_name"]),
        transport=transport,
        command=str(command) if command else None,
        args=[str(item) for item in args] if isinstance(args, list) else [],
        url=str(url) if url else None,
        env=env,
        cwd=str(cwd) if cwd else str(project_root()),
    )


def local_mcp_configs(enabled_servers: list[str] | None = None) -> list[MCPServerConfig]:
    base_env = {
        "PYTHONPATH": pythonpath_env(),
        "PATH": os.environ.get("PATH", ""),
    }
    configs = [
        config
        for row in list_mcp_servers()
        if (config := _config_from_row(row, base_env)) is not None
    ]
    if enabled_servers is None:
        return configs
    enabled = set(enabled_servers)
    return [config for config in configs if config.server_name in enabled]


def allow_write_tools() -> bool:
    return os.environ.get("MCP_ALLOW_WRITE_TOOLS", "false").lower() in {"1", "true", "yes"}


def dynamic_mcp_enabled() -> bool:
    return os.environ.get("MCP_DYNAMIC_TOOLS_ENABLED", "true").lower() in {"1", "true", "yes"}
