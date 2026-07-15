import argparse
from typing import Any

from supportagent.mcp_servers.teams_mcp.tools import TEAMS_TOOLS


def register_tools(mcp: Any) -> None:
    for tool in TEAMS_TOOLS:
        mcp.tool(description=tool.__doc__ or tool.__name__)(tool)


def create_server() -> Any:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("teams_mcp")
    register_tools(mcp)
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Microsoft Teams/Graph MCP server")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable_http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()

    mcp = create_server()
    try:
        mcp.run(transport=args.transport, host=args.host, port=args.port)
    except TypeError:
        mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
