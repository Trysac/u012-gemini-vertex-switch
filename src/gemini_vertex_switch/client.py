"""Gemini generateContent client for AI Studio and Vertex AI."""

from __future__ import annotations

import http.client
import json
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from .config import GeminiConfig, endpoint, is_valid_secret, validate_config
from .errors import GeminiError, clip
from .port import LLMPort, Message
from .transport import Transport, UrllibTransport

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

MAX_REQUEST_BYTES = 4_194_304
_ROLES = ("system", "user", "assistant")
_MAX_API_MESSAGE_CHARS = 200
_MAX_REASON_CHARS = 64

EventCallback = Callable[[dict[str, object]], None]


@dataclass(frozen=True)
class GenerateResult:
    """Parsed generateContent response."""

    text: str
    finish_reason: str | None
    prompt_tokens: int | None
    output_tokens: int | None
    raw: dict[str, object] = field(repr=False)


def _config_error(message: str) -> GeminiError:
    return GeminiError("config", message)


def _encode_body(
    contents: Sequence[Mapping[str, object]],
    system_instruction: str | None,
    generation_config: Mapping[str, object] | None,
) -> bytes:
    if not isinstance(contents, (list, tuple)) or not contents:
        raise _config_error("contents must be a non-empty list of mappings")
    if not all(isinstance(item, Mapping) for item in contents):
        raise _config_error("contents must be a non-empty list of mappings")
    body: dict[str, object] = {"contents": [dict(item) for item in contents]}
    if system_instruction is not None:
        if not isinstance(system_instruction, str):
            raise _config_error("system_instruction must be a string")
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    if generation_config is not None:
        if not isinstance(generation_config, Mapping):
            raise _config_error("generation_config must be a mapping")
        body["generationConfig"] = dict(generation_config)
    try:
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError):
        raise _config_error("request is not JSON serializable") from None
    if len(raw) > MAX_REQUEST_BYTES:
        raise _config_error("request body exceeds the size limit")
    return raw


def _api_message(data: bytes, secret: str) -> str | None:
    try:
        payload = json.loads(data)
    except (ValueError, RecursionError):
        return None
    error = payload.get("error") if isinstance(payload, dict) else None
    message = error.get("message") if isinstance(error, dict) else None
    if not isinstance(message, str):
        return None
    if secret:
        message = message.replace(secret, "***")
    return message[:_MAX_API_MESSAGE_CHARS]


def _parse_json(data: bytes) -> dict[str, object]:
    try:
        payload = json.loads(data)
    except (ValueError, RecursionError):
        raise GeminiError("invalid_response", "response is not valid JSON") from None
    if not isinstance(payload, dict):
        raise GeminiError("invalid_response", "response is not a JSON object")
    return payload


def _int_or_none(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _usage(payload: dict[str, object]) -> tuple[int | None, int | None]:
    metadata = payload.get("usageMetadata")
    if not isinstance(metadata, dict):
        return None, None
    prompt = _int_or_none(metadata.get("promptTokenCount"))
    output = _int_or_none(metadata.get("candidatesTokenCount"))
    return prompt, output


def _block_reason(payload: dict[str, object]) -> str | None:
    feedback = payload.get("promptFeedback")
    reason = feedback.get("blockReason") if isinstance(feedback, dict) else None
    return clip(reason, _MAX_REASON_CHARS) if isinstance(reason, str) else None


def _candidate_text(candidate: dict[str, object]) -> str:
    content = candidate.get("content")
    if content is None:
        return ""
    if not isinstance(content, dict):
        raise GeminiError("invalid_response", "candidate content is not an object")
    parts = content.get("parts")
    if parts is None:
        return ""
    if not isinstance(parts, list):
        raise GeminiError("invalid_response", "candidate parts are not a list")
    texts: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            raise GeminiError("invalid_response", "candidate part is not an object")
        text = part.get("text")
        if isinstance(text, str) and part.get("thought") is not True:
            texts.append(text)
    return "".join(texts)


class GeminiClient(LLMPort):
    """Calls Gemini ``generateContent`` on AI Studio or Vertex AI.

    The transport and the Vertex token provider are injectable so tests never touch the
    network. Keys and tokens are never stored in ``repr``, errors, logs or events.
    """

    def __init__(
        self,
        config: GeminiConfig,
        *,
        transport: Transport | None = None,
        token_provider: Callable[[], str] | None = None,
        timeout: float = 60.0,
        max_response_bytes: int = 10_485_760,
        on_event: EventCallback | None = None,
    ) -> None:
        """Validate ``config`` and prepare the request URL.

        Raises:
            GeminiError: ``config`` code for missing or invalid settings, including a Vertex
                config without ``token_provider``.
        """
        extra = ["token_provider"] if config.backend == "vertex" and token_provider is None else []
        self._config = validate_config(config, extra_missing=extra)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise _config_error("timeout must be a positive number")
        if (
            isinstance(max_response_bytes, bool)
            or not isinstance(max_response_bytes, int)
            or max_response_bytes < 1
        ):
            raise _config_error("max_response_bytes must be a positive integer")
        self._url = endpoint(self._config)
        self._token_provider = token_provider
        self._timeout = float(timeout)
        self._max_response_bytes = max_response_bytes
        self._transport: Transport = (
            transport if transport is not None else UrllibTransport(max_response_bytes)
        )
        self._on_event = on_event

    def __repr__(self) -> str:
        return f"GeminiClient(config={self._config!r}, timeout={self._timeout!r})"

    def complete(self, messages: Sequence[Message], *, max_tokens: int) -> str:
        """Send a chat and return the reply text.

        System messages are joined into ``systemInstruction``; ``assistant`` becomes ``model``;
        ``max_tokens`` becomes ``generationConfig.maxOutputTokens``.

        Raises:
            GeminiError: for invalid input or any API failure.
        """
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1:
            raise _config_error("max_tokens must be a positive integer")
        if isinstance(messages, (str, bytes)) or not isinstance(messages, Sequence):
            raise _config_error("messages must be a sequence")
        system_parts: list[str] = []
        contents: list[Mapping[str, object]] = []
        for message in messages:
            if not isinstance(message, Mapping):
                raise _config_error("invalid message")
            role = message.get("role")
            content = message.get("content")
            if role not in _ROLES or not isinstance(content, str):
                raise _config_error("invalid message")
            if role == "system":
                system_parts.append(content)
            else:
                gemini_role = "user" if role == "user" else "model"
                contents.append({"role": gemini_role, "parts": [{"text": content}]})
        if not contents:
            raise _config_error("at least one user or assistant message is required")
        result = self.generate(
            contents,
            system_instruction="\n\n".join(system_parts) if system_parts else None,
            generation_config={"maxOutputTokens": max_tokens},
        )
        return result.text

    def generate(
        self,
        contents: Sequence[Mapping[str, object]],
        *,
        system_instruction: str | None = None,
        generation_config: Mapping[str, object] | None = None,
    ) -> GenerateResult:
        """Call ``generateContent`` with raw Gemini ``contents``.

        Raises:
            GeminiError: ``config`` for invalid input, ``http`` for non-2xx or transport
                failures, ``response_too_large``, ``invalid_response`` or ``empty_response``.
        """
        body = _encode_body(contents, system_instruction, generation_config)
        headers, secret = self._auth_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        status, data = self._post(headers, body)
        if not 200 <= status < 300:
            self._emit(status, None, None)
            message = _api_message(data, secret)
            detail = f"HTTP {status}" if message is None else f"HTTP {status}: {message}"
            raise GeminiError("http", detail, status=status, api_message=message)
        payload = _parse_json(data)
        prompt_tokens, output_tokens = _usage(payload)
        self._emit(status, prompt_tokens, output_tokens)
        candidates = payload.get("candidates")
        if candidates is None or (isinstance(candidates, list) and not candidates):
            reason = _block_reason(payload)
            detail = "response has no candidates"
            if reason is not None:
                detail += f" (blockReason={reason})"
            raise GeminiError("empty_response", detail, reason=reason)
        if not isinstance(candidates, list) or not isinstance(candidates[0], dict):
            raise GeminiError("invalid_response", "candidates are malformed")
        candidate = candidates[0]
        finish = candidate.get("finishReason")
        return GenerateResult(
            text=_candidate_text(candidate),
            finish_reason=finish if isinstance(finish, str) else None,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            raw=payload,
        )

    def _auth_headers(self) -> tuple[dict[str, str], str]:
        if self._config.backend == "ai_studio":
            key = self._config.api_key or ""
            return {"x-goog-api-key": key}, key
        provider = self._token_provider
        if provider is None:
            raise GeminiError("config", "token_provider is required", missing=["token_provider"])
        try:
            token = provider()
        except Exception:
            logger.debug("token_provider raised")
            raise GeminiError("config", "token_provider failed") from None
        if not is_valid_secret(token):
            raise GeminiError("config", "token_provider returned an invalid token")
        return {"Authorization": f"Bearer {token}"}, token

    def _post(self, headers: Mapping[str, str], body: bytes) -> tuple[int, bytes]:
        try:
            status, data = self._transport.post(self._url, headers, body, self._timeout)
        except (OSError, http.client.HTTPException) as exc:
            logger.debug("transport failure: %s", type(exc).__name__)
            raise GeminiError("http", f"transport failure: {type(exc).__name__}") from None
        if not isinstance(status, int) or not isinstance(data, (bytes, bytearray)):
            raise GeminiError("invalid_response", "transport returned an invalid result")
        if len(data) > self._max_response_bytes:
            raise GeminiError("response_too_large", "response body too large")
        return status, bytes(data)

    def _emit(
        self,
        status: int,
        prompt_tokens: int | None,
        output_tokens: int | None,
    ) -> None:
        logger.debug(
            "gemini response backend=%s model=%s status=%d",
            self._config.backend,
            self._config.model,
            status,
        )
        callback = self._on_event
        if callback is None:
            return
        event: dict[str, object] = {
            "backend": self._config.backend,
            "model": self._config.model,
            "status": status,
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
        }
        try:
            callback(event)
        except Exception:
            logger.warning("on_event callback raised")
