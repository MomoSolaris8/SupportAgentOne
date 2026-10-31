from supportagent.core.language import ResponseLanguage

# Fixed fallback wording from architecture-proposal-v0.1.de.md, section 6.4.
REFUSAL_TEXT = (
    "Ich kann diese Frage anhand der verfügbaren Quellen nicht verlässlich beantworten.\n"
    "Bitte prüfen Sie die offiziellen Versicherungsbedingungen oder eskalieren Sie an das "
    "zuständige Fachteam."
)

# The model marks these cases instead of writing them out, so the code can detect them in any
# answer language and replace them with fixed wording.
INSUFFICIENT_EVIDENCE_MARKER = "[[INSUFFICIENT_EVIDENCE]]"
TERM_NOT_DEFINED_MARKER = "[[TERM_NOT_DEFINED]]"

REFUSAL_TEXTS: dict[ResponseLanguage, str] = {
    "de": REFUSAL_TEXT,
    "en": (
        "I cannot reliably answer this question based on the available sources.\n"
        "Please check the official insurance terms or escalate to the responsible "
        "specialist team."
    ),
    "zh": "我无法根据现有资料可靠地回答这个问题。\n请查阅正式的保险条款，或转交负责的专业团队处理。",
}

TERM_NOT_DEFINED_TEXTS: dict[ResponseLanguage, str] = {
    "de": "Dieser Begriff ist in den freigegebenen Quellen nicht ausdrücklich definiert.",
    "en": "This term is not explicitly defined in the approved sources.",
    "zh": "该术语在已批准的资料中没有明确定义。",
}
