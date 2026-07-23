import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from supportagent.auth.store import auth_connection, get_user_by_email  # noqa: E402
from supportagent.claims.store import (  # noqa: E402
    add_audit_event,
    create_claim_schema,
    insert_claim,
    insert_document,
)


def seed(owner_email: str) -> tuple[int, int]:
    fixtures = json.loads((ROOT / "data" / "synthetic_claims.json").read_text())
    conn = auth_connection()
    try:
        create_claim_schema(conn)
        user_record = get_user_by_email(conn, owner_email.strip().casefold())
        if user_record is None:
            raise SystemExit(f"No registered user found for {owner_email!r}. Register in the app first.")
        user, _ = user_record
        claims_created = 0
        documents_created = 0
        for fixture in fixtures:
            existing = conn.execute(
                "SELECT owner_user_id FROM claims WHERE id = %s",
                (fixture["id"],),
            ).fetchone()
            if existing:
                if existing[0] != user.id:
                    raise SystemExit(
                        f"Synthetic claim {fixture['id']} already belongs to another user; refusing to reassign it."
                    )
                continue
            claim = insert_claim(
                conn,
                {
                    "id": fixture["id"],
                    "owner_user_id": user.id,
                    "policy_id": fixture["policy_id"],
                    "product_line": fixture["product_line"],
                    "policy_version": fixture["policy_version"],
                    "jurisdiction": fixture["jurisdiction"],
                    "customer_reference": fixture["customer_reference"],
                    "claim_type": fixture["claim_type"],
                    "status": "DRAFT",
                },
            )
            for index, document in enumerate(fixture["documents"], start=1):
                insert_document(
                    conn,
                    {
                        "id": f"{fixture['id']}-DOC-{index:02d}",
                        "claim_id": claim.id,
                        "document_type": document["document_type"],
                        "filename": f"{document['document_type']}.pdf",
                        "extraction_status": document["status"],
                        "extracted_fields": {"synthetic": True},
                    },
                )
                documents_created += 1
            add_audit_event(
                conn,
                claim.id,
                user.id,
                "SYNTHETIC_CLAIM_SEEDED",
                {"fixture_id": fixture["id"]},
            )
            claims_created += 1
        conn.commit()
        return claims_created, documents_created
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed synthetic Claim review data for an existing user.")
    parser.add_argument("--owner-email", required=True, help="Registered SupportAgent user email.")
    parser.add_argument("--yes", action="store_true", help="Required acknowledgement that synthetic data will be written.")
    args = parser.parse_args()
    if not args.yes:
        raise SystemExit("Refusing to write demo data without --yes.")
    load_dotenv(ROOT / ".env")
    claims, documents = seed(args.owner_email)
    print(f"Seeded {claims} synthetic claims and {documents} documents for {args.owner_email}.")


if __name__ == "__main__":
    main()
