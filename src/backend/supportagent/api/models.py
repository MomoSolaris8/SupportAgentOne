from pydantic import BaseModel

from supportagent.llm import get_model_options


class ChatModel(BaseModel):
    id: str
    label: str
    provider: str
    capabilities: list[str]
    description: str
    default: bool


class ChatModelsResponse(BaseModel):
    models: list[ChatModel]


def chat_models() -> ChatModelsResponse:
    return ChatModelsResponse(
        models=[
            ChatModel(
                id=model.id,
                label=model.label,
                provider=model.provider,
                capabilities=list(model.capabilities),
                description=model.description,
                default=model.default,
            )
            for model in get_model_options()
        ]
    )
