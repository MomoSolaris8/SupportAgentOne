import os

from openai import OpenAI

from supportagent.llm import resolve_chat_model
from supportagent.memory.schemas import ChatMessage, LongMemory

# Fixed fallback wording from architecture-proposal-v0.1.de.md, section 6.4.
REFUSAL_TEXT = (
    "Ich kann diese Frage anhand der verfügbaren Quellen nicht verlässlich beantworten.\n"
    "Bitte prüfen Sie die offiziellen Versicherungsbedingungen oder eskalieren Sie an das "
    "zuständige Fachteam."
)

SYSTEM_PROMPT = f"""Du bist ein Assistent für ein internes Versicherungs-Wissensportal.

Beantworte fachliche Versicherungsfragen ausschließlich auf Basis der nummerierten \
Quellenausschnitte, die der Nutzer dir gibt. Antworte auf Deutsch.

Wenn der Nutzer ein Bild hochgeladen hat und nach sichtbaren Bildinhalten fragt, darfst du \
die Bildbeobachtungen verwenden. Verwende Bildbeobachtungen aber nicht als Beleg fuer \
Deckung, Leistung, Haftung, Betrug, Schadenhoehe oder finale Regulierung.

Zitiere die verwendeten Quellen mit ihrer Nummer in eckigen Klammern, z. B. [1] oder [2][3].

Halte das Antwortformat stabil:

1. Beginne mit genau einem kurzen Einleitungssatz, der die Frage direkt beantwortet.
2. Wenn mehrere Punkte genannt werden, verwende danach eine Markdown-Bullet-Liste.
3. Jeder Bullet muss dieses Format haben:
   - **Name**: Beschreibung mit Quellenangabe [1].
4. Verwende keine Tabellen und keine frei wechselnden Zwischenüberschriften.
5. Erkläre keine normalisierten Tippfehler, wenn die normalisierte Frage eindeutig ist.

Erfinde keine Policen-, Leistungs- oder Prozessdetails, die nicht in den Quellen stehen.

Bevorzuge bei widersprüchlichen Quellen freigegebene Confluence-Inhalte gegenüber \
Jira-Tickets und weise darauf hin, wenn ein Jira-Ticket auf eine mögliche \
Dokumentationslücke hindeutet.

Wenn die Quellen nicht ausreichen, um die Frage verlässlich zu beantworten, antworte exakt \
mit folgendem Text und sonst nichts:

{REFUSAL_TEXT}

Gib niemals beides aus. Entscheide dich entweder für eine vollständige Antwort mit Zitaten \
oder für den Ablehnungstext, nie für beides zusammen."""

IMAGE_ONLY_SYSTEM_PROMPT = """Du bist ein Assistent fuer ein internes Versicherungs-Wissensportal.

Der Nutzer hat ein Bild hochgeladen, aber es wurden keine verlaesslichen Wissensquellen aus
Confluence oder Jira gefunden. Antworte deshalb nur auf Basis der Bildbeobachtung.

Regeln:
1. Antworte auf Deutsch.
2. Beschreibe nur sichtbare oder extrahierte Inhalte aus der Bildbeobachtung.
3. Triff keine Aussage zu Deckung, Leistung, Haftung, Betrug, Schadenhoehe oder finaler Regulierung.
4. Wenn keine Bildanalyse verfuegbar ist, sage das klar.
5. Wenn der Nutzer eine fachliche Versicherungsfrage stellt, erklaere kurz, dass dafuer zusaetzliche Quellen oder Fachpruefung noetig sind."""


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
        return response.choices[0].message.content

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
            {
                "role": "user",
                "content": f"{memory_context}\n\n{skill_context}\n\n{image_context}\n\nFrage: {question}\n\nQuellen:\n{context}",
            },
        ],
        temperature=0,
    )
    return response.choices[0].message.content
