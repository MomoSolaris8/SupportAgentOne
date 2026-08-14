from datetime import datetime, timezone

from psycopg.types.json import Jsonb

from supportagent.claims.store import update_review_run


class RecordingCursor:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class RecordingConnection:
    def __init__(self):
        self.query = ""
        self.params = ()

    def execute(self, query, params):
        self.query = query
        self.params = params
        now = datetime.now(timezone.utc)
        return RecordingCursor(
            ("run-1", "claim-1", "SUCCEEDED", "COMPLETED", None, None, now, now, now)
        )


def test_review_result_is_written_as_jsonb():
    conn = RecordingConnection()

    update_review_run(
        conn,
        "run-1",
        status="SUCCEEDED",
        current_step="COMPLETED",
        result={"claim_id": "claim-1"},
        complete=True,
    )

    assert "result = COALESCE(%s, result)" in conn.query
    assert isinstance(conn.params[2], Jsonb)
    assert conn.params[2].obj == {"claim_id": "claim-1"}
