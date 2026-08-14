from supportagent.skills import get_skill_instructions, list_skills


def test_skills_load_from_skill_md_files():
    skills = list_skills()
    skill_ids = {skill["skill_id"] for skill in skills}

    assert skill_ids == {
        "claim_intake",
        "coverage_explanation",
        "document_checklist",
        "escalation_triage",
        "policy_comparison",
    }
    assert all(skill["instruction"].startswith("# ") for skill in skills)


def test_get_skill_instructions_filters_selected_skills():
    instructions = get_skill_instructions(["claim_intake", "missing_skill"])

    assert len(instructions) == 1
    assert "# Claim Intake" in instructions[0]
    assert "incident date/time" in instructions[0]
