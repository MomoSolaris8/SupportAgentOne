from pydantic import BaseModel

from supportagent.llm import get_chat_model_options


class ChatModel(BaseModel):
    id: str
    label: str
    default: bool


class ChatModelsResponse(BaseModel):
    models: list[ChatModel]


def chat_models() -> ChatModelsResponse:
    return ChatModelsResponse(
        models=[
            ChatModel(id=model.id, label=model.label, default=model.default)
            for model in get_chat_model_options()
        ]
    )
