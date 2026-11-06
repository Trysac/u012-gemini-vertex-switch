"""The LLM port and deterministic test doubles."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal, Protocol, TypedDict

DEFAULT_MAX_CALLS = 1000


class Message(TypedDict):
    """One chat message."""

    role: Literal["system", "user", "assistant"]
    content: str


class LLMPort(Protocol):
    """Anything that can complete a chat."""

    def complete(self, messages: Sequence[Message], *, max_tokens: int) -> str:
        """Return the model reply for ``messages``."""


class RecordingExhaustedError(Exception):
    """Raised by :class:`RecordedLLM` when all recorded replies were used."""

    code = "recording_exhausted"


def _snapshot(messages: Sequence[Message]) -> list[Message]:
    return [{"role": m["role"], "content": m["content"]} for m in messages]


def _remember(calls: list[list[Message]], messages: Sequence[Message], max_calls: int) -> None:
    calls.append(_snapshot(messages))
    if len(calls) > max_calls:
        del calls[: len(calls) - max_calls]


class RecordedLLM:
    """Returns the given replies in order and records every request in ``calls``."""

    def __init__(self, replies: Sequence[str], *, max_calls: int = DEFAULT_MAX_CALLS) -> None:
        self._replies = tuple(replies)
        self._index = 0
        self._max_calls = max_calls
        self.calls: list[list[Message]] = []

    def complete(self, messages: Sequence[Message], *, max_tokens: int) -> str:
        """Return the next recorded reply or raise :class:`RecordingExhaustedError`."""
        _remember(self.calls, messages, self._max_calls)
        if self._index >= len(self._replies):
            raise RecordingExhaustedError("no recorded replies left")
        reply = self._replies[self._index]
        self._index += 1
        return reply


class FakeLLM:
    """Returns ``fn(messages)`` and records every request in ``calls``."""

    def __init__(
        self,
        fn: Callable[[Sequence[Message]], str],
        *,
        max_calls: int = DEFAULT_MAX_CALLS,
    ) -> None:
        self._fn = fn
        self._max_calls = max_calls
        self.calls: list[list[Message]] = []

    def complete(self, messages: Sequence[Message], *, max_tokens: int) -> str:
        """Return the result of the wrapped function."""
        _remember(self.calls, messages, self._max_calls)
        return self._fn(messages)
