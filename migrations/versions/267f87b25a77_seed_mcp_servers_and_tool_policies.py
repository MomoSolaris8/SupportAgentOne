"""seed mcp servers and tool policies

Revision ID: 267f87b25a77
Revises: 863e47af17d2
Create Date: 2026-10-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '267f87b25a77'
down_revision: Union[str, Sequence[str], None] = '863e47af17d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed the default MCP servers and their tool policies."""
    # Values are copied, not imported: this migration must insert the same rows
    # forever, even after the constants in mcp_client/store.py change.
    # Servers first: mcp_tool_policies.server_name references mcp_servers.
    op.execute(
        """
        INSERT INTO mcp_servers (server_name, display_name, transport, config, enabled)
        VALUES
            ('time_mcp', 'Local timezone-aware time MCP server', 'stdio',
             '{"command": "python", "args": ["-m", "supportagent.mcp_servers.time_mcp", "--transport", "stdio"]}',
             true),
            ('weather_mcp', 'Local Google Weather MCP server', 'stdio',
             '{"command": "python", "args": ["-m", "supportagent.mcp_servers.weather_mcp", "--transport", "stdio"]}',
             true),
            ('teams_mcp', 'Local Microsoft Graph MCP server', 'stdio',
             '{"command": "python", "args": ["-m", "supportagent.mcp_servers.teams_mcp", "--transport", "stdio"]}',
             true)
        ON CONFLICT (server_name) DO NOTHING
        """
    )
    # Columns: enabled, auto_allowed, requires_confirmation.
    # Read-only tools run automatically, write tools need confirmation,
    # and tools a personal Microsoft account cannot use are disabled.
    op.execute(
        """
        INSERT INTO mcp_tool_policies
            (server_name, tool_name, enabled, auto_allowed, requires_confirmation)
        VALUES
            ('time_mcp', 'get_current_time',                true, true, false),
            ('weather_mcp', 'get_weather',                  true, true, false),
            ('teams_mcp', 'get_my_profile',                 true, true, false),
            ('teams_mcp', 'batch_get_user_info',            false, false, false),
            ('teams_mcp', 'create_calendar',                true, false, true),
            ('teams_mcp', 'delete_calendar',                true, false, true),
            ('teams_mcp', 'get_calendar_info',              true, true, false),
            ('teams_mcp', 'get_calendars_list',             true, true, false),
            ('teams_mcp', 'update_calendar',                true, false, true),
            ('teams_mcp', 'create_calendar_event',          true, false, true),
            ('teams_mcp', 'create_default_calendar_event',  true, false, true),
            ('teams_mcp', 'append_calendar_event_attendee', true, false, true),
            ('teams_mcp', 'get_calendar_event',             true, true, false),
            ('teams_mcp', 'update_calendar_event',          true, false, true),
            ('teams_mcp', 'delete_calendar_event',          true, false, true),
            ('teams_mcp', 'create_document',                true, false, true),
            ('teams_mcp', 'get_document',                   true, true, false),
            ('teams_mcp', 'create_folder',                  true, false, true),
            ('teams_mcp', 'list_folder_files',              true, true, false),
            ('teams_mcp', 'list_chats',                     false, false, false),
            ('teams_mcp', 'create_message',                 false, false, false)
        ON CONFLICT (server_name, tool_name) DO NOTHING
        """
    )


def downgrade() -> None:
    """Keep the rows.

    Existing databases already had these rows before this migration ran, and
    deleting a server cascades to users' saved credentials.
    """
