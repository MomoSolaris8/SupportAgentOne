from dataclasses import dataclass
import re

@dataclass(frozen=True)
class QueryRewrite:
    original_query: str
    normalized_query: str
    rewritten_query: str
    changed: bool
    reason: str

TYPO_NORMALIZATIONS = {
      r"\bversichrrung\b": "versicherung",
      r"\bverisicherung\b": "versicherung",
      r"\bversicherrung\b": "versicherung",
      r"\bverischerung\b": "versicherung",
  }

REWRITE_RULES = {
      "autounfall": ["Kfz-Schadenmeldung", "Verkehrsunfall"],
      "schaden": ["Schadenmeldung", "Deckung", "Versicherungsfall"],
      "schadigung": ["Schadenmeldung", "Deckung", "Versicherungsfall"],
      "schädigung": ["Schadenmeldung", "Deckung", "Versicherungsfall"],
      "schägung": ["Schadenmeldung", "Deckung", "Versicherungsfall"],
      "unterlagen": ["erforderliche Unterlagen"],
      "brauche": ["erforderliche Unterlagen"],
      "geklaut": ["Diebstahl", "Ausschlüsse"],
      "diebstahl": ["Diebstahl", "Ausschlüsse"],
  }

def normalize_typos(question: str) -> tuple[str, list[str]]:
    normalized = question
    applied: list[str] = []
    for pattern, replacement in TYPO_NORMALIZATIONS.items():
        next_normalized, count = re.subn(pattern, replacement, normalized, flags=re.IGNORECASE)
        if count:
            applied.append(f"{pattern} -> {replacement}")
            normalized = next_normalized
    return normalized, applied


def rewrite_query(question: str) -> QueryRewrite:
    normalized_question, typo_changes = normalize_typos(question)
    normalized = normalized_question.lower()

    expansions = []

    if "autounfall" in normalized:
        expansions.extend(["Kfz-Schadenmeldung", "Verkehrsunfall"])

    if (
        "schaden" in normalized
        or "schadigung" in normalized
        or "schädigung" in normalized
        or "schägung" in normalized
    ):
        expansions.extend(["Schadenmeldung", "Deckung", "Versicherungsfall"])

    if "unterlagen" in normalized or "brauche" in normalized:
        expansions.append("erforderliche Unterlagen")

    if "geklaut" in normalized or "diebstahl" in normalized:
        expansions.extend(["Diebstahl", "Ausschlüsse"])

    if not expansions:
        return QueryRewrite(
            original_query=question,
            normalized_query=normalized_question,
            rewritten_query=normalized_question,
            changed=bool(typo_changes),
            reason=(
                "Normalized common typos."
                if typo_changes
                else "No rewrite rules matched."
            ),
        )

    rewritten = f"{normalized_question} {' '.join(expansions)}"

    return QueryRewrite(
        original_query=question,
        normalized_query=normalized_question,
        rewritten_query=rewritten,
        changed=True,
        reason=(
            "Normalized common typos and added domain terminology for retrieval."
            if typo_changes
            else "Added domain terminology for retrieval."
        ),
    )
