from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RouteDecision:
    source: Literal["confluence", "jira", "both"]
    reason: str

def route_question(question: str) -> RouteDecision:
    normalized_question = question.lower()

    jira_keywords = [
        "jira",
        "ticket",
        "issue",
        "dokumentationslücke",
        "dokumentationsluecke",
        "unklar",
        "klärungsbedarf",
        "klaerungsbedarf",
    ]

    confluence_keywords = [
        "unterlagen",
        "prozess",
        "versicherung",
        "bedingungen",
        "schadenmeldung",
        "deckung",
        "ausschluss",
    ]
    if any(keyword in normalized_question for keyword in jira_keywords):
        return RouteDecision(
            source="jira",
            reason="Question appears to ask about tickets or documentation gaps.",
        )

    if any(keyword in normalized_question for keyword in confluence_keywords):
        return RouteDecision(
            source="confluence",
            reason="Question appears to ask for approved insurance knowledge.",
        )

    return RouteDecision(
        source="both",
        reason="No specific source intent detected.",
    )
