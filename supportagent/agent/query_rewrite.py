from dataclasses import dataclass

@dataclass(frozen=True)
class QueryRewrite:
    original_query: str
    rewritten_query: str
    changed: bool
    reason: str

REWRITE_RULES = {
      "autounfall": ["Kfz-Schadenmeldung", "Verkehrsunfall"],
      "unterlagen": ["erforderliche Unterlagen"],
      "brauche": ["erforderliche Unterlagen"],
      "geklaut": ["Diebstahl", "Ausschlüsse"],
      "diebstahl": ["Diebstahl", "Ausschlüsse"],
  }

def rewrite_query(question: str) -> QueryRewrite:
    normalized = question.lower()

    expansions = []

    if "autounfall" in normalized:
        expansions.extend(["Kfz-Schadenmeldung", "Verkehrsunfall"])

    if "unterlagen" in normalized or "brauche" in normalized:
        expansions.append("erforderliche Unterlagen")

    if "geklaut" in normalized or "diebstahl" in normalized:
        expansions.extend(["Diebstahl", "Ausschlüsse"])

    if not expansions:
        return QueryRewrite(
            original_query=question,
            rewritten_query=question,
            changed=False,
            reason="No rewrite rules matched.",
        )

    rewritten = f"{question} {' '.join(expansions)}"

    return QueryRewrite(
        original_query=question,
        rewritten_query=rewritten,
        changed=True,
        reason="Added domain terminology for retrieval.",
    )