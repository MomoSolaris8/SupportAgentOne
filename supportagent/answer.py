import os

from openai import OpenAI

# Fixed fallback wording from architecture-proposal-v0.1.de.md, section 6.4.
REFUSAL_TEXT = (
    "Ich kann diese Frage anhand der verfügbaren Quellen nicht verlässlich beantworten.\n"
    "Bitte prüfen Sie die offiziellen Versicherungsbedingungen oder eskalieren Sie an das "
    "zuständige Fachteam."
)

SYSTEM_PROMPT = f"""Du bist ein Assistent für ein internes Versicherungs-Wissensportal.

Beantworte die Frage ausschließlich auf Basis der nummerierten Quellenausschnitte, die der \
Nutzer dir gibt. Antworte auf Deutsch.

Zitiere die verwendeten Quellen mit ihrer Nummer in eckigen Klammern, z. B. [1] oder [2][3].

Erfinde keine Policen-, Leistungs- oder Prozessdetails, die nicht in den Quellen stehen.

Bevorzuge bei widersprüchlichen Quellen freigegebene Confluence-Inhalte gegenüber \
Jira-Tickets und weise darauf hin, wenn ein Jira-Ticket auf eine mögliche \
Dokumentationslücke hindeutet.

Wenn die Quellen nicht ausreichen, um die Frage verlässlich zu beantworten, antworte exakt \
mit folgendem Text und sonst nichts:

{REFUSAL_TEXT}"""


def generate_answer(question: str, chunks: list[dict]) -> str:
    if not chunks:
        return REFUSAL_TEXT

    client = OpenAI(
        api_key=os.environ["EMBEDDING_API_KEY"],
        base_url=os.environ["EMBEDDING_BASE_URL"],
    )
    model = os.environ.get("CHAT_MODEL", "qwen-plus")

    context = "\n\n".join(
        f"[{i}] ({chunk['metadata']['source']}) {chunk['metadata']['title']}\n{chunk['content']}"
        for i, chunk in enumerate(chunks, start=1)
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Frage: {question}\n\nQuellen:\n{context}"},
        ],
    )
    return response.choices[0].message.content
