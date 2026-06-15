"""Run the basic evaluation questions against the live /ask pipeline.

Requires a running pgvector instance with indexed chunks (see index.py) and
valid EMBEDDING_*/CHAT_MODEL credentials. Prints a pass/fail report per
question for manual review of the generated answers.
"""

from .answer import generate_answer
from dotenv import load_dotenv
from .eval_questions import EVAL_QUESTIONS
from .retrieval import retrieve

# Two key phrases from REFUSAL_TEXT, used for a lenient match since the model
# may vary whitespace/line breaks slightly when reproducing the wording.
_REFUSAL_PHRASES = [
    "nicht verlässlich beantworten",
    "zuständige Fachteam",
]


def run() -> None:
    load_dotenv()

    passed = 0
    for case in EVAL_QUESTIONS:
        chunks = retrieve(case["question"])
        retrieved_titles = {chunk["metadata"]["title"] for chunk in chunks}
        answer = generate_answer(case["question"], chunks)

        print(f"\nFrage ({case['type']}): {case['question']}")

        if case.get("expect_refusal"):
            ok = all(phrase in answer for phrase in _REFUSAL_PHRASES)
            print(f"  Ablehnung erwartet: {'OK' if ok else 'FAIL'}")
        else:
            missing = [t for t in case["expected_sources"] if t not in retrieved_titles]
            ok = not missing
            print(f"  Erwartete Quellen gefunden: {'OK' if ok else f'FAIL (fehlend: {missing})'}")

        passed += ok
        print(f"  Antwort: {answer}")

    print(f"\n{passed}/{len(EVAL_QUESTIONS)} Faelle bestanden")


if __name__ == "__main__":
    run()
