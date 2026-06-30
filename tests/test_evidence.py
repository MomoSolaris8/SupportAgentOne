from supportagent.agent.evidence import check_evidence


def test_evidence_is_insufficient_without_chunks():
      decision = check_evidence([])

      assert decision.status == "insufficient"


def test_evidence_is_sufficient_with_chunks():
      decision = check_evidence([
          {"content": "fake chunk", "metadata": {}, "distance": 0.1}
      ])

      assert decision.status == "sufficient"