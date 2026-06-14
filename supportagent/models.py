from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Document:
    text: str
    metadata: dict[str, Any]
