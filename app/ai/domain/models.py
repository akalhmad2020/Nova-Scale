from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LLMRequest:
    messages: tuple[LLMMessage, ...]
    temperature: float = 0.2


@dataclass(frozen=True, slots=True)
class LLMResponse:
    content: str
    model: str
