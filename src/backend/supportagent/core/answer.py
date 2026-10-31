from supportagent.core.language import (
    LANGUAGE_NAMES,
    ResponseLanguage,
    detect_response_language,
)
from supportagent.llm import LLMTask, complete_chat
from supportagent.memory.schemas import ChatMessage, LongMemory
from supportagent.prompts.insurance_knowledge import (
    FEW_SHOT_MESSAGES,
    IMAGE_ONLY_SYSTEM_PROMPT,
    INSUFFICIENT_EVIDENCE_MARKER,
    REFUSAL_TEXTS,
    SYSTEM_PROMPT,
    TERM_NOT_DEFINED_MARKER,
    TERM_NOT_DEFINED_TEXTS,
)


IMAGE_FOCUSED_TERMS = (
    "bild",
    "foto",
    "image",
    "screenshot",
    "anhang",
    "datei",
    "hochgeladen",
    "uploaded",
    "siehst du",
    "steht dort",
    "was steht",
    "analysiere",
    "beschreibe",
    "lesen",
    "read",
    "extract",
    "ocr",
)


def is_image_focused_question(question: str) -> bool:
    normalized = question.casefold()
    return any(term in normalized for term in IMAGE_FOCUSED_TERMS)


def format_short_memory(messages: list[ChatMessage]) -> str:
    if not messages:
        return "Keine bisherige Unterhaltung in diesem Thread."
    return "\n".join(f"- {message.role}: {message.content}" for message in messages)


def format_long_memories(memories: list[LongMemory]) -> str:
    if not memories:
        return "Keine relevanten Langzeit-Erinnerungen."
    return "\n".join(f"- {memory.content}" for memory in memories)


def refusal_text(question: str) -> str:
    return REFUSAL_TEXTS[detect_response_language(question)]


def enforce_answer_contract(answer: str, language: ResponseLanguage = "de") -> str:
    """Replace the model's evidence markers with fixed wording in the answer language."""
    normalized = answer.strip()
    if INSUFFICIENT_EVIDENCE_MARKER in normalized:
        return REFUSAL_TEXTS[language]
    if TERM_NOT_DEFINED_MARKER in normalized:
        clarification = normalized.replace(TERM_NOT_DEFINED_MARKER, "").strip()
        return f"{TERM_NOT_DEFINED_TEXTS[language]} {clarification}".strip()
    return normalized


def answer_reports_insufficient_evidence(answer: str) -> bool:
    return answer in REFUSAL_TEXTS.values() or answer.startswith(
        tuple(TERM_NOT_DEFINED_TEXTS.values())
    )


def generate_answer(
    question: str,
    chunks: list[dict],
    short_history: list[ChatMessage] | None = None,
    long_memories: list[LongMemory] | None = None,
    skill_instructions: list[str] | None = None,
    image_contexts: list[str] | None = None,
    model: str | None = None,
    task: LLMTask = "chat",
) -> str:
    language = detect_response_language(question)
    if not chunks and not image_contexts:
        return REFUSAL_TEXTS[language]

    response_language = LANGUAGE_NAMES[language]

    if image_contexts and (not chunks or is_image_focused_question(question)):
        image_context_text = "\n\n".join(image_contexts)
        response = complete_chat(
            [
                {"role": "system", "content": IMAGE_ONLY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Bildbeobachtungen:\n"
                        f"{image_context_text}\n\n"
                        f"Frage: {question}\n\n"
                        f"Antwortsprache: {response_language}"
                    ),
                },
            ],
            requested_model=model,
            task=task,
            temperature=0,
        )
        return enforce_answer_contract(response.content, language)

    context = "\n\n".join(
        f"[{i}] ({chunk['metadata']['source']}) {chunk['metadata']['title']}\n{chunk['content']}"
        for i, chunk in enumerate(chunks, start=1)
    )
    memory_context = (
        "Kurzzeitgedaechtnis aus diesem Thread:\n"
        f"{format_short_memory(short_history or [])}\n\n"
        "Langzeitgedaechtnis zum Nutzer. Verwende es nur fuer Praeferenzen, Rolle und "
        "Kontext, niemals als fachliche Versicherungsquelle:\n"
        f"{format_long_memories(long_memories or [])}"
    )
    skill_context = (
        "Aktive Insurance Skills:\n"
        + ("\n".join(f"- {instruction}" for instruction in skill_instructions) if skill_instructions else "Keine.")
    )
    image_context = (
        "Bildbeobachtungen aus hochgeladenen Dateien:\n"
        + ("\n\n".join(image_contexts) if image_contexts else "Keine.")
        + "\n\nWichtig: Bildbeobachtungen duerfen fuer sichtbare Bildinhalte verwendet werden. "
        "Nutze sie nicht als fachliche Versicherungsquelle. Policen-, Prozess- und "
        "Leistungsdetails muessen weiterhin aus den nummerierten Quellen belegt werden."
    )

    response = complete_chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            *FEW_SHOT_MESSAGES,
            {
                "role": "user",
                "content": (
                    f"{memory_context}\n\n{skill_context}\n\n{image_context}\n\n"
                    f"Frage: {question}\n\nAntwortsprache: {response_language}\n\n"
                    f"Quellen:\n{context}"
                ),
            },
        ],
        requested_model=model,
        task=task,
        temperature=0,
    )
    return enforce_answer_contract(response.content, language)
