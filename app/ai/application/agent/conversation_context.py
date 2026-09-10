from dataclasses import dataclass
from typing import Literal

ConversationRole = Literal[
    "user",
    "assistant",
]


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    role: ConversationRole
    content: str


@dataclass(frozen=True, slots=True)
class ConversationContext:
    messages: tuple[ConversationMessage, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.messages
