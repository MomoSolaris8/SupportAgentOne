from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class EvidenceDecision:
      status: Literal["sufficient", "insufficient"]
      reason: str


def check_evidence(chunks: list[dict]) -> EvidenceDecision:
      if not chunks:
          return EvidenceDecision(
              status="insufficient",
              reason="No chunks were retrieved.",
          )

      return EvidenceDecision(
          status="sufficient",
          reason="At least one chunk was retrieved.",
      )