from supportagent.agent.router import route_question

def test_route_jira_question():
    decision = route_question("Gibt es ein Jira Ticket zur Dokumentationslücke?")

    assert decision.source == "jira"


def test_route_confluence_question():
    decision = route_question("Welche Unterlagen brauche ich fuer eine Schadenmeldung?")

    assert decision.source == "confluence"


def test_route_unknown_question_to_both():
    decision = route_question("Was ist der aktuelle Stand?")

    assert decision.source == "both"
