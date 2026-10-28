import pytest
from pydantic import ValidationError

from supportagent.claims.schemas import ClaimDecisionRequest


def test_rejecting_claim_requires_a_reason():
    with pytest.raises(ValidationError, match="reason is required"):
        ClaimDecisionRequest(decision="REJECT")
