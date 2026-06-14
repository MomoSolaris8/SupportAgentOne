"""Basic evaluation questions for the /ask endpoint (Meilenstein 4).

Each case checks whether retrieval surfaces the expected source pages/issues
(by title) and, for the refusal case, whether the model produces the fixed
controlled-refusal wording from architecture-proposal-v0.1.de.md, 6.4.
"""

EVAL_QUESTIONS = [
    {
        "question": "Welche Gefahren sind in der Hausratversicherung im Standardtarif versichert?",
        "type": "single_source",
        "expected_sources": ["Hausratversicherung - Leistungsuebersicht"],
    },
    {
        "question": (
            "Was muss ich nach einem Kfz-Unfall einreichen und mit welcher "
            "Selbstbeteiligung muss ich rechnen?"
        ),
        "type": "multi_source_synthesis",
        "expected_sources": [
            "Kfz-Schaden - Ablauf, Selbstbeteiligung und Unterlagen",
            "Schadenmeldung - Prozessablauf und benoetigte Unterlagen",
        ],
    },
    {
        "question": "Wie ist das Wetter morgen in Berlin?",
        "type": "refusal",
        "expect_refusal": True,
    },
    {
        "question": (
            "Wie schnell muss ich einen Leitungswasserschaden an meiner "
            "Wohngebaeudeversicherung melden?"
        ),
        "type": "conflicting_sources",
        "expected_sources": [
            "Schadenmeldung - Prozessablauf und benoetigte Unterlagen",
            "Unklare Meldefrist bei Leitungswasserschaden: Hausrat vs. Wohngebaeude",
        ],
    },
    {
        "question": "Ist mein Fahrrad versichert, wenn es vor dem Supermarkt gestohlen wird?",
        "type": "terminology_robustness",
        "expected_sources": [
            "Hausratversicherung - Leistungsuebersicht",
            "Onboarding-Frage: Ist Fahrraddiebstahl ausserhalb der Wohnung ueber Hausrat versichert?",
        ],
    },
    {
        "question": (
            "Werden Mediationskosten bei einem Streit mit dem Nachbarn von "
            "Rechtsschutz Premium uebernommen?"
        ),
        "type": "multi_source_synthesis",
        "expected_sources": [
            "Rechtsschutzversicherung - Leistungsuebersicht und Ausschluesse",
            "Frage: Deckt Rechtsschutz Premium Mediationskosten bei Nachbarschaftsstreit ab?",
        ],
    },
    {
        "question": "Wann wird ein Schadenfall an den Fachbereich Recht eskaliert?",
        "type": "single_source",
        "expected_sources": ["Eskalationsprozesse in der Schadenbearbeitung"],
    },
    {
        "question": "Muss ich bei einem Steinschlagschaden an der Windschutzscheibe eine Selbstbeteiligung zahlen?",
        "type": "multi_source_synthesis",
        "expected_sources": [
            "Kfz-Schaden - Ablauf, Selbstbeteiligung und Unterlagen",
            "Selbstbeteiligung bei Kfz-Teilkasko nach Glasschaden uneinheitlich kommuniziert",
        ],
    },
]
