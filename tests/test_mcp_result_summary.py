import json

from supportagent.api.mcp import _summarize_tool_result


def test_calendar_result_summary_keeps_user_fields_and_hides_graph_internals():
    result = json.dumps(
        {
            "subject": "Harness agent test",
            "start": {
                "dateTime": "2026-07-21T17:00:00.0000000",
                "timeZone": "W. Europe Standard Time",
            },
            "end": {
                "dateTime": "2026-07-21T18:00:00.0000000",
                "timeZone": "W. Europe Standard Time",
            },
            "webLink": "https://outlook.example/event",
            "bodyPreview": "Details: Sharon Chen, Alex Wu",
            "body": {"contentType": "html", "content": "<html>internal</html>"},
            "organizer": {"emailAddress": {"address": "private@example.com"}},
            "responseStatus": {"response": "organizer"},
            "hideAttendees": False,
        }
    )

    summary = _summarize_tool_result(result)

    assert "- subject: Harness agent test" in summary
    assert "- start: 2026-07-21T17:00:00.0000000" in summary
    assert "- end: 2026-07-21T18:00:00.0000000" in summary
    assert "- webLink: https://outlook.example/event" in summary
    assert "- bodyPreview: Details: Sharon Chen, Alex Wu" in summary
    assert "private@example.com" not in summary
    assert "<html>" not in summary
    assert "responseStatus" not in summary
    assert "hideAttendees" not in summary
