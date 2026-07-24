from typing import Any, Protocol

from supportagent.llm.schemas import ChatCompletion, ModelProfile


class ChatProvider(Protocol):
    def complete(
        self,
        profile: ModelProfile,
        messages: list[dict[str, Any]],
        *,
        temperature: float | None = 0,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> ChatCompletion: ...
