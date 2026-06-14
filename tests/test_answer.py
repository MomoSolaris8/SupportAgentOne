from supportagent.answer import REFUSAL_TEXT, generate_answer


def test_generate_answer_refuses_when_no_chunks_are_retrieved():
    assert generate_answer("Was ist versichert?", []) == REFUSAL_TEXT
