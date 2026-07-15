from fastapi import Depends
from pydantic import BaseModel

from supportagent.auth.dependencies import get_current_user
from supportagent.auth.schemas import AuthUser
from supportagent.skills import list_skills


class SkillResponse(BaseModel):
    skill_id: str
    name: str
    category: str
    description: str
    instruction: str


class SkillsResponse(BaseModel):
    skills: list[SkillResponse]


def skills(user: AuthUser = Depends(get_current_user)) -> SkillsResponse:
    return SkillsResponse(skills=[SkillResponse(**skill) for skill in list_skills()])
