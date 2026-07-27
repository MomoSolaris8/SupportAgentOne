from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field
from pydantic.fields import FieldInfo

from supportagent.mcp_servers.http import ToolConfigurationError


DEFAULT_TIMEZONE = "Europe/Zurich"


def _current_datetime(timezone: ZoneInfo) -> datetime:
    return datetime.now(timezone)


def get_current_time(
    timezone: str = Field(
        default=DEFAULT_TIMEZONE,
        description="IANA timezone name, e.g. Europe/Zurich or America/New_York.",
    ),
) -> dict[str, Any]:
    """Get the current date and time for an IANA timezone."""
    timezone = DEFAULT_TIMEZONE if isinstance(timezone, FieldInfo) else timezone
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise ToolConfigurationError(
            f"Unknown IANA timezone: {timezone}. Use a value such as Europe/Zurich."
        ) from error

    current = _current_datetime(zone)
    return {
        "timezone": timezone,
        "datetime": current.isoformat(timespec="seconds"),
        "date": current.date().isoformat(),
        "time": current.strftime("%H:%M:%S"),
        "utc_offset": current.strftime("%z"),
    }


TIME_TOOLS = [get_current_time]
