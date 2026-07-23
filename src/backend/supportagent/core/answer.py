import os

from openai import OpenAI

from supportagent.llm import resolve_chat_model
from supportagent.memory.schemas import ChatMessage, LongMemory
from supportagent.prompts.insurance_knowledge import (
    FEW_SHOT_MESSAGES,
    IMAGE_ONLY_SYSTEM_PROMPT,
    REFUSAL_TEXT,
    SYSTEM_PROMPT,
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


def enforce_answer_contract(answer: str) -> str:
    """Keep the model from mixing a sourced answer with the fixed refusal."""
    normalized = answer.strip()
    if "Ich kann diese Frage anhand der verfügbaren Quellen nicht verlässlich beantworten." in normalized:
        return REFUSAL_TEXT
    return normalized


def answer_reports_insufficient_evidence(answer: str) -> bool:
    normalized = answer.casefold()
    return answer == REFUSAL_TEXT or (
        "in den freigegebenen quellen" in normalized
        and "nicht ausdrücklich definiert" in normalized
    )


def generate_answer(
    question: str,
    chunks: list[dict],
    short_history: list[ChatMessage] | None = None,
    long_memories: list[LongMemory] | None = None,
    skill_instructions: list[str] | None = None,
    image_contexts: list[str] | None = None,
    model: str | None = None,
) -> str:
    if not chunks and not image_contexts:
        return REFUSAL_TEXT

    client = OpenAI(
        api_key=os.environ["EMBEDDING_API_KEY"],
        base_url=os.environ["EMBEDDING_BASE_URL"],
    )
    chat_model = resolve_chat_model(model)

    if image_contexts and (not chunks or is_image_focused_question(question)):
        image_context_text = "\n\n".join(image_contexts)
        response = client.chat.completions.create(
            model=chat_model,
            messages=[
                {"role": "system", "content": IMAGE_ONLY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Bildbeobachtungen:\n"
                        f"{image_context_text}\n\n"
                        f"Frage: {question}"
                    ),
                },
            ],
            temperature=0,
        )
        return enforce_answer_contract(response.choices[0].message.content)

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

    response = client.chat.completions.create(
        model=chat_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *FEW_SHOT_MESSAGES,
            {
                "role": "user",
                "content": f"{memory_context}\n\n{skill_context}\n\n{image_context}\n\nFrage: {question}\n\nQuellen:\n{context}",
            },
        ],
        temperature=0,
    )
    return enforce_answer_contract(response.choices[0].message.content)
