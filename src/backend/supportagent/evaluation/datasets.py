import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CLAIM_EVAL_PATH = PROJECT_ROOT / "evals" / "claim_review.jsonl"
DEFAULT_CLAIM_FIXTURES_PATH = PROJECT_ROOT / "data" / "synthetic_claims.json"
DEFAULT_RAG_EVAL_PATH = PROJECT_ROOT / "evals" / "rag_qa.jsonl"


class ClaimReviewEvalCase(BaseModel):
    case_id: str
    claim_fixture: str
    expected_missing: list[str]
    expected_proposal: str | None = None
    forbidden_executions: list[str]


class ClaimDocumentFixture(BaseModel):
    document_type: str
    status: str


class ClaimFixture(BaseModel):
    id: str
    policy_id: str
    product_line: str
    policy_version: str | None = None
    jurisdiction: str
    customer_reference: str
    claim_type: str
    documents: list[ClaimDocumentFixture]
    expected: dict[str, Any]


class RAGEvalCase(BaseModel):
    case_id: str
    question: str
    category: str
    expected_sources: list[str]
    expect_refusal: bool = False


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_claim_review_cases(path: Path = DEFAULT_CLAIM_EVAL_PATH) -> list[ClaimReviewEvalCase]:
    return [ClaimReviewEvalCase.model_validate(item) for item in load_jsonl(path)]


def load_claim_fixtures(
    path: Path = DEFAULT_CLAIM_FIXTURES_PATH,
) -> dict[str, ClaimFixture]:
    items = json.loads(path.read_text(encoding="utf-8"))
    fixtures = [ClaimFixture.model_validate(item) for item in items]
    return {fixture.id: fixture for fixture in fixtures}


def load_rag_eval_cases(path: Path = DEFAULT_RAG_EVAL_PATH) -> list[RAGEvalCase]:
    return [RAGEvalCase.model_validate(item) for item in load_jsonl(path)]


def dataset_fingerprint(*paths: Path) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"
