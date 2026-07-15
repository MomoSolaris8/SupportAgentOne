import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InsuranceSkill:
    skill_id: str
    name: str
    category: str
    description: str
    instruction: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def skills_root() -> Path:
    return Path(__file__).resolve().parent / "insurance"


def _read_skill_metadata(path: Path) -> dict[str, Any]:
    metadata_path = path / "skill.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing skill metadata: {metadata_path}")
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _read_skill_instruction(path: Path) -> str:
    instruction_path = path / "SKILL.md"
    if not instruction_path.exists():
        raise FileNotFoundError(f"Missing skill instruction: {instruction_path}")
    return instruction_path.read_text(encoding="utf-8").strip()


def _load_skill(path: Path) -> InsuranceSkill:
    metadata = _read_skill_metadata(path)
    instruction = _read_skill_instruction(path)
    return InsuranceSkill(
        skill_id=str(metadata["skill_id"]),
        name=str(metadata["name"]),
        category=str(metadata["category"]),
        description=str(metadata["description"]),
        instruction=instruction,
    )


@lru_cache(maxsize=1)
def load_skills() -> tuple[InsuranceSkill, ...]:
    root = skills_root()
    if not root.exists():
        return ()

    skills = [
        _load_skill(path)
        for path in sorted(root.iterdir())
        if path.is_dir() and not path.name.startswith(".")
    ]
    skill_ids = [skill.skill_id for skill in skills]
    if len(skill_ids) != len(set(skill_ids)):
        raise ValueError("Duplicate skill_id found in skill files.")
    return tuple(skills)


def list_skills() -> list[dict[str, str]]:
    return [skill.to_dict() for skill in load_skills()]


def get_skill_instructions(enabled_skill_ids: list[str] | None) -> list[str]:
    if not enabled_skill_ids:
        return []
    selected = set(enabled_skill_ids)
    return [skill.instruction for skill in load_skills() if skill.skill_id in selected]


def reload_skills() -> tuple[InsuranceSkill, ...]:
    load_skills.cache_clear()
    return load_skills()
