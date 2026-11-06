"""One Gemini generateContent client for AI Studio and Vertex AI."""

from __future__ import annotations

import logging

from .client import GeminiClient, GenerateResult
from .config import GeminiConfig, resolve_config
from .errors import GeminiError
from .port import FakeLLM, LLMPort, Message, RecordedLLM, RecordingExhaustedError
from .transport import Transport

__all__ = [
    "FakeLLM",
    "GeminiClient",
    "GeminiConfig",
    "GeminiError",
    "GenerateResult",
    "LLMPort",
    "Message",
    "RecordedLLM",
    "RecordingExhaustedError",
    "Transport",
    "__version__",
    "resolve_config",
]

__version__ = "0.1.0"

logging.getLogger(__name__).addHandler(logging.NullHandler())
