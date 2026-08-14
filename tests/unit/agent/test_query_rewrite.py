from supportagent.agent.query_rewrite import rewrite_query


def test_rewrite_adds_domain_terms_for_autounfall():
      rewrite = rewrite_query("Was brauche ich nach einem Autounfall?")

      assert rewrite.original_query == "Was brauche ich nach einem Autounfall?"
      assert rewrite.changed is True
      assert "Kfz-Schadenmeldung" in rewrite.rewritten_query
      assert "Verkehrsunfall" in rewrite.rewritten_query
      assert "erforderliche Unterlagen" in rewrite.rewritten_query


def test_rewrite_adds_domain_terms_for_theft():
      rewrite = rewrite_query("Mein Fahrrad wurde aus dem Keller geklaut.")

      assert rewrite.changed is True
      assert "Diebstahl" in rewrite.rewritten_query
      assert "Ausschlüsse" in rewrite.rewritten_query


def test_rewrite_keeps_query_when_no_rule_matches():
      rewrite = rewrite_query("Was ist der aktuelle Stand?")

      assert rewrite.original_query == "Was ist der aktuelle Stand?"
      assert rewrite.normalized_query == "Was ist der aktuelle Stand?"
      assert rewrite.rewritten_query == "Was ist der aktuelle Stand?"
      assert rewrite.changed is False


def test_rewrite_normalizes_common_insurance_typos():
      rewrite = rewrite_query("versichrrung")

      assert rewrite.original_query == "versichrrung"
      assert rewrite.normalized_query == "versicherung"
      assert rewrite.rewritten_query == "versicherung"
      assert rewrite.changed is True


def test_rewrite_uses_normalized_query_for_domain_expansion():
      rewrite = rewrite_query("Welche verisicherung deckt einen Schaden?")

      assert "versicherung" in rewrite.normalized_query.lower()
      assert "Verisicherung" not in rewrite.rewritten_query
      assert "Schadenmeldung" in rewrite.rewritten_query
