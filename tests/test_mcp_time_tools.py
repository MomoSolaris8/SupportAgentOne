from datetime import datetime, timezone

import pytest

from supportagent.mcp_servers.http import ToolConfigurationError
from supportagent.mcp_servers.registry import get_tool, list_tools
from supportagent.mcp_servers.time_mcp import tools


def test_current_time_uses_requested_timezone(monkeypatch):
    fixed_utc = datetime(2026, 7, 26, 12, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(
        tools,
        "_current_datetime",
        lambda zone: fixed_utc.astimezone(zone),
    )

    result = tools.get_current_time(timezone="Europe/Zurich")

    assert result == {
        "timezone": "Europe/Zurich",
        "datetime": "2026-07-26T14:30:00+02:00",
        "date": "2026-07-26",
        "time": "14:30:00",
        "utc_offset": "+0200",
    }


def test_current_time_defaults_to_zurich(monkeypatch):
    fixed_utc = datetime(2026, 1, 26, 12, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(
        tools,
        "_current_datetime",
        lambda zone: fixed_utc.astimezone(zone),
    )

    result = tools.get_current_time()

    assert result["timezone"] == "Europe/Zurich"
    assert result["time"] == "13:30:00"
    assert result["utc_offset"] == "+0100"


def test_current_time_rejects_unknown_timezone():
    with pytest.raises(ToolConfigurationError, match="Unknown IANA timezone"):
        tools.get_current_time(timezone="Zurich")


def test_current_time_is_registered_as_an_mcp_tool():
    descriptor = next(
        item
        for item in list_tools()
        if item["server"] == "time_mcp" and item["name"] == "get_current_time"
    )

    assert get_tool("time_mcp", "get_current_time") is tools.get_current_time
    assert descriptor["example_arguments"] == {"timezone": "Europe/Zurich"}
