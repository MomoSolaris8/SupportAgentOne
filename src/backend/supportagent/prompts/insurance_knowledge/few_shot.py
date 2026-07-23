from .contract import REFUSAL_TEXT

# These examples are a stable prompt prefix. They teach response boundaries and formatting;
# their synthetic source text must never be treated as runtime insurance evidence.
FEW_SHOT_MESSAGES: tuple[dict[str, str], ...] = (
    {
        "role": "user",
        "content": (
            "<example type=\"terminology_supported\">\n"
            "Frage: Was bedeutet der Begriff Meldefrist?\n\n"
            "Quellen:\n"
            "[1] (confluence) Beispiel-Handbuch\n"
            "In diesem Beispiel bezeichnet die Meldefrist den dokumentierten Zeitraum, "
            "innerhalb dessen eine Meldung eingereicht werden muss.\n"
            "</example>"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Die **Meldefrist** ist der dokumentierte Zeitraum, innerhalb dessen eine "
            "Meldung eingereicht werden muss [1]."
        ),
    },
    {
        "role": "user",
        "content": (
            "<example type=\"terminology_unsupported\">\n"
            "Frage: Was ist Schädigung?\n\n"
            "Quellen:\n"
            "[1] (confluence) Beispiel-Schadenmeldung\n"
            "Der Text beschreibt einzureichende Unterlagen, definiert den erfragten "
            "Begriff jedoch nicht.\n"
            "</example>"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Der Begriff **„Schädigung“** ist in den freigegebenen Quellen nicht "
            "ausdrücklich definiert. Meinen Sie einen Schaden, ein Schadenereignis oder "
            "die Verursachung eines Schadens?"
        ),
    },
    {
        "role": "user",
        "content": (
            "<example type=\"high_risk_unsupported\">\n"
            "Frage: Wird mein Schaden vollständig bezahlt?\n\n"
            "Quellen:\n"
            "[1] (jira) Beispiel-Ticket\n"
            "Das Ticket erwähnt eine offene Prüfung, enthält aber keine Police und keine "
            "Deckungsentscheidung.\n"
            "</example>"
        ),
    },
    {
        "role": "assistant",
        "content": REFUSAL_TEXT,
    },
)
