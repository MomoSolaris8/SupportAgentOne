from supportagent.prompts.insurance_knowledge import (
    FEW_SHOT_MESSAGES,
    PROMPT_VERSION,
    REFUSAL_TEXT,
    SYSTEM_PROMPT,
)


def test_prompt_is_versioned_and_process_driven():
    assert PROMPT_VERSION == "insurance-knowledge-v2.0"
    assert "# Entscheidungsprozess" in SYSTEM_PROMPT
    assert "`terminology`" in SYSTEM_PROMPT
    assert "`policy_question`" in SYSTEM_PROMPT
    assert "`claim_operation`" in SYSTEM_PROMPT
    assert "Thematische Ähnlichkeit genügt nicht." in SYSTEM_PROMPT


def test_prompt_keeps_memory_and_examples_outside_evidence_boundary():
    assert "Frühere Nachrichten und Erinnerungen" in SYSTEM_PROMPT
    assert "Few-shot-Beispiele" in SYSTEM_PROMPT
    assert "keine Wissensquellen" in SYSTEM_PROMPT


def test_few_shot_examples_cover_three_decision_boundaries():
    assert len(FEW_SHOT_MESSAGES) == 6
    user_examples = FEW_SHOT_MESSAGES[::2]
    assistant_examples = FEW_SHOT_MESSAGES[1::2]

    assert all(message["role"] == "user" for message in user_examples)
    assert all(message["role"] == "assistant" for message in assistant_examples)
    assert 'type="terminology_supported"' in user_examples[0]["content"]
    assert 'type="terminology_unsupported"' in user_examples[1]["content"]
    assert 'type="high_risk_unsupported"' in user_examples[2]["content"]
    assert assistant_examples[2]["content"] == REFUSAL_TEXT
