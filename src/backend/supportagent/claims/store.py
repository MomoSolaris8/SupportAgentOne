from typing import Any

import psycopg
from psycopg.types.json import Json

from supportagent.claims.schemas import Claim, ClaimDocument, ProposedAction


def ensure_claim_schema() -> None:
    from supportagent.rag.vector_store import get_connection

    conn = get_connection()
    try:
        create_claim_schema(conn)
    finally:
        conn.close()


def create_claim_schema(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS claims (
            id TEXT PRIMARY KEY,
            owner_user_id TEXT NOT NULL,
            policy_id TEXT NOT NULL,
            product_line TEXT NOT NULL DEFAULT 'unknown',
            policy_version TEXT,
            jurisdiction TEXT NOT NULL DEFAULT 'DE',
            customer_reference TEXT NOT NULL,
            claim_type TEXT NOT NULL,
            incident_date TEXT,
            status TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute("ALTER TABLE claims ADD COLUMN IF NOT EXISTS product_line TEXT NOT NULL DEFAULT 'unknown'")
    conn.execute("ALTER TABLE claims ADD COLUMN IF NOT EXISTS policy_version TEXT")
    conn.execute("ALTER TABLE claims ADD COLUMN IF NOT EXISTS jurisdiction TEXT NOT NULL DEFAULT 'DE'")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS claim_documents (
            id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
            uploaded_file_id TEXT,
            document_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            extraction_status TEXT NOT NULL DEFAULT 'PENDING',
            extracted_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS proposed_actions (
            id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
            run_id TEXT,
            action_type TEXT NOT NULL,
            tool_server TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments JSONB NOT NULL DEFAULT '{}'::jsonb,
            reason TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            status TEXT NOT NULL,
            proposed_by TEXT NOT NULL,
            approved_by TEXT,
            approved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS claim_action_approvals (
            id BIGSERIAL PRIMARY KEY,
            proposed_action_id TEXT NOT NULL REFERENCES proposed_actions(id) ON DELETE CASCADE,
            actor_user_id TEXT NOT NULL,
            decision TEXT NOT NULL CHECK (decision IN ('APPROVED', 'REJECTED')),
            comment TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS claim_audit_events (
            id BIGSERIAL PRIMARY KEY,
            claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
            actor_user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS claims_owner_updated_idx ON claims (owner_user_id, updated_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS claim_documents_claim_idx ON claim_documents (claim_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS proposed_actions_claim_idx ON proposed_actions (claim_id, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS claim_audit_claim_idx ON claim_audit_events (claim_id, created_at)")
    conn.commit()


def _claim(row: tuple[Any, ...]) -> Claim:
    return Claim(
        id=row[0], owner_user_id=row[1], policy_id=row[2], customer_reference=row[3],
        claim_type=row[4], incident_date=row[5], status=row[6],
        created_at=row[7].isoformat(), updated_at=row[8].isoformat(),
        product_line=row[9], policy_version=row[10], jurisdiction=row[11],
    )


def _document(row: tuple[Any, ...]) -> ClaimDocument:
    return ClaimDocument(
        id=row[0], claim_id=row[1], uploaded_file_id=row[2], document_type=row[3],
        filename=row[4], extraction_status=row[5], extracted_fields=row[6] or {},
        created_at=row[7].isoformat(),
    )


def _action(row: tuple[Any, ...]) -> ProposedAction:
    return ProposedAction(
        id=row[0], claim_id=row[1], run_id=row[2], action_type=row[3],
        tool_server=row[4], tool_name=row[5], arguments=row[6] or {}, reason=row[7],
        risk_level=row[8], status=row[9], proposed_by=row[10], approved_by=row[11],
        approved_at=row[12].isoformat() if row[12] else None,
        created_at=row[13].isoformat(), updated_at=row[14].isoformat(),
    )


CLAIM_SELECT = """
    SELECT id, owner_user_id, policy_id, customer_reference, claim_type,
           incident_date, status, created_at, updated_at,
           product_line, policy_version, jurisdiction
    FROM claims
"""

ACTION_SELECT = """
    SELECT proposed_actions.id, proposed_actions.claim_id, proposed_actions.run_id,
           proposed_actions.action_type, proposed_actions.tool_server,
           proposed_actions.tool_name, proposed_actions.arguments,
           proposed_actions.reason, proposed_actions.risk_level,
           proposed_actions.status, proposed_actions.proposed_by,
           proposed_actions.approved_by, proposed_actions.approved_at,
           proposed_actions.created_at, proposed_actions.updated_at
    FROM proposed_actions
"""


def insert_claim(conn: psycopg.Connection, values: dict[str, Any]) -> Claim:
    row = conn.execute(
        """
        INSERT INTO claims (
            id, owner_user_id, policy_id, customer_reference, claim_type,
            incident_date, status, product_line, policy_version, jurisdiction
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, owner_user_id, policy_id, customer_reference, claim_type,
                  incident_date, status, created_at, updated_at,
                  product_line, policy_version, jurisdiction
        """,
        (values["id"], values["owner_user_id"], values["policy_id"], values["customer_reference"],
         values["claim_type"], values.get("incident_date"), values["status"],
         values["product_line"], values.get("policy_version"), values["jurisdiction"]),
    ).fetchone()
    return _claim(row)


def fetch_claim(conn: psycopg.Connection, claim_id: str, owner_user_id: str) -> Claim | None:
    row = conn.execute(CLAIM_SELECT + " WHERE id = %s AND owner_user_id = %s", (claim_id, owner_user_id)).fetchone()
    return _claim(row) if row else None


def fetch_claims(conn: psycopg.Connection, owner_user_id: str) -> list[Claim]:
    rows = conn.execute(CLAIM_SELECT + " WHERE owner_user_id = %s ORDER BY updated_at DESC", (owner_user_id,)).fetchall()
    return [_claim(row) for row in rows]


def insert_document(conn: psycopg.Connection, values: dict[str, Any]) -> ClaimDocument:
    row = conn.execute(
        """
        INSERT INTO claim_documents (
            id, claim_id, uploaded_file_id, document_type, filename, extraction_status, extracted_fields
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, claim_id, uploaded_file_id, document_type, filename,
                  extraction_status, extracted_fields, created_at
        """,
        (values["id"], values["claim_id"], values.get("uploaded_file_id"), values["document_type"],
         values["filename"], values["extraction_status"], Json(values.get("extracted_fields", {}))),
    ).fetchone()
    return _document(row)


def fetch_documents(conn: psycopg.Connection, claim_id: str) -> list[ClaimDocument]:
    rows = conn.execute(
        """
        SELECT id, claim_id, uploaded_file_id, document_type, filename,
               extraction_status, extracted_fields, created_at
        FROM claim_documents WHERE claim_id = %s ORDER BY created_at
        """,
        (claim_id,),
    ).fetchall()
    return [_document(row) for row in rows]


def insert_action(conn: psycopg.Connection, values: dict[str, Any]) -> ProposedAction:
    row = conn.execute(
        """
        INSERT INTO proposed_actions (
            id, claim_id, run_id, action_type, tool_server, tool_name, arguments,
            reason, risk_level, status, proposed_by
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, claim_id, run_id, action_type, tool_server, tool_name, arguments,
                  reason, risk_level, status, proposed_by, approved_by, approved_at,
                  created_at, updated_at
        """,
        (values["id"], values["claim_id"], values.get("run_id"), values["action_type"],
         values["tool_server"], values["tool_name"], Json(values.get("arguments", {})),
         values["reason"], values["risk_level"], values["status"], values["proposed_by"]),
    ).fetchone()
    return _action(row)


def fetch_actions(conn: psycopg.Connection, claim_id: str) -> list[ProposedAction]:
    rows = conn.execute(ACTION_SELECT + " WHERE claim_id = %s ORDER BY created_at DESC", (claim_id,)).fetchall()
    return [_action(row) for row in rows]


def fetch_action_for_owner(
    conn: psycopg.Connection, action_id: str, claim_id: str, owner_user_id: str, *, for_update: bool = False
) -> ProposedAction | None:
    suffix = " FOR UPDATE" if for_update else ""
    row = conn.execute(
        ACTION_SELECT + " JOIN claims ON claims.id = proposed_actions.claim_id "
        "WHERE proposed_actions.id = %s AND proposed_actions.claim_id = %s AND claims.owner_user_id = %s" + suffix,
        (action_id, claim_id, owner_user_id),
    ).fetchone()
    return _action(row) if row else None


def record_action_decision(
    conn: psycopg.Connection, action_id: str, actor_user_id: str, decision: str, comment: str | None
) -> ProposedAction:
    conn.execute(
        """
        INSERT INTO claim_action_approvals (proposed_action_id, actor_user_id, decision, comment)
        VALUES (%s, %s, %s, %s)
        """,
        (action_id, actor_user_id, decision, comment),
    )
    row = conn.execute(
        """
        UPDATE proposed_actions
        SET status = %s,
            approved_by = CASE WHEN %s = 'APPROVED' THEN %s ELSE NULL END,
            approved_at = CASE WHEN %s = 'APPROVED' THEN now() ELSE NULL END,
            updated_at = now()
        WHERE id = %s
        RETURNING id, claim_id, run_id, action_type, tool_server, tool_name, arguments,
                  reason, risk_level, status, proposed_by, approved_by, approved_at,
                  created_at, updated_at
        """,
        (decision, decision, actor_user_id, decision, action_id),
    ).fetchone()
    return _action(row)


def add_audit_event(
    conn: psycopg.Connection, claim_id: str, actor_user_id: str, event_type: str, payload: dict[str, Any]
) -> None:
    conn.execute(
        "INSERT INTO claim_audit_events (claim_id, actor_user_id, event_type, payload) VALUES (%s, %s, %s, %s)",
        (claim_id, actor_user_id, event_type, Json(payload)),
    )
