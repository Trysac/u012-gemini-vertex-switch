"""Typed errors for gemini_vertex_switch."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

ErrorCode = Literal["config", "http", "empty_response", "response_too_large", "invalid_response"]

MAX_ERROR_MESSAGE_CHARS = 200


def clip(text: str, limit: int = MAX_ERROR_MESSAGE_CHARS) -> str:
    """Return ``text`` cut to at most ``limit`` characters."""
    return text if len(text) <= limit else text[:limit]


class GeminiError(Exception):
    """Base error of the library.

    Attributes:
        code: Stable machine-readable error code.
        missing: Names of missing settings (``config`` errors).
        status: HTTP status (``http`` errors, when a response was received).
        api_message: Redacted ``error.message`` from the API, at most 200 characters.
        reason: Prompt block reason (``empty_response`` errors).
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        missing: Sequence[str] = (),
        status: int | None = None,
        api_message: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(clip(message))
        self.code: ErrorCode = code
        self.missing: list[str] = list(missing)
        self.status = status
        self.api_message = api_message
        self.reason = reason
