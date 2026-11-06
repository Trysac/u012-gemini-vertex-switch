"""Backend resolution and validation for Gemini requests."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Literal

from .errors import GeminiError

Backend = Literal["ai_studio", "vertex"]

AI_STUDIO_HOST = "generativelanguage.googleapis.com"
DEFAULT_LOCATION = "global"

_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PROJECT_RE = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_LOCATION_RE = re.compile(r"^[a-z]+(-[a-z0-9]+)*$")
_VERSION_RE = re.compile(r"^v[0-9]{1,3}((alpha|beta)[0-9]{0,3})?$")
_SECRET_RE = re.compile(r"^[\x21-\x7e]{1,4096}$")
_OVERRIDE_KEYS = frozenset({"backend", "project", "location", "api_key", "api_version"})
_MAX_FIELD_CHARS = 256
_MAX_LOCATION_CHARS = 63
_MAX_SECRET_CHARS = 4096
_MODEL_PREFIX = "models/"


@dataclass(frozen=True)
class GeminiConfig:
    """Resolved settings for one Gemini backend.

    ``project`` and ``location`` are used by Vertex only; ``api_key`` by AI Studio only.
    The key is excluded from ``repr``.
    """

    backend: Backend
    model: str
    project: str | None
    location: str | None
    api_version: str
    api_key: str | None = field(default=None, repr=False)


def _check(
    pattern: re.Pattern[str],
    value: object,
    name: str,
    max_len: int = _MAX_FIELD_CHARS,
) -> None:
    if not isinstance(value, str) or len(value) > max_len or pattern.fullmatch(value) is None:
        raise GeminiError("config", f"invalid {name}")


def is_valid_secret(value: object) -> bool:
    """Return True for a non-empty printable-ASCII string without whitespace."""
    return (
        isinstance(value, str)
        and len(value) <= _MAX_SECRET_CHARS
        and _SECRET_RE.fullmatch(value) is not None
    )


def _normalize_model(model: object) -> object:
    if isinstance(model, str) and model.startswith(_MODEL_PREFIX):
        return model[len(_MODEL_PREFIX) :]
    return model


def validate_config(
    config: GeminiConfig,
    *,
    extra_missing: Sequence[str] = (),
) -> GeminiConfig:
    """Validate ``config`` and return it with the ``models/`` prefix stripped.

    Raises:
        GeminiError: ``config`` code for missing or invalid settings.
    """
    if config.backend not in ("ai_studio", "vertex"):
        raise GeminiError("config", "invalid backend")
    missing: list[str] = []
    if config.backend == "ai_studio":
        if not config.api_key:
            missing.append("GOOGLE_API_KEY")
    else:
        if not config.project:
            missing.append("GOOGLE_CLOUD_PROJECT")
        if not config.location:
            missing.append("GOOGLE_CLOUD_LOCATION")
    missing.extend(extra_missing)
    if missing:
        raise GeminiError(
            "config",
            "missing configuration: " + ", ".join(missing),
            missing=missing,
        )
    model = _normalize_model(config.model)
    _check(_MODEL_RE, model, "model")
    _check(_VERSION_RE, config.api_version, "api_version")
    if config.backend == "ai_studio":
        if not is_valid_secret(config.api_key):
            raise GeminiError("config", "invalid api_key")
    else:
        _check(_PROJECT_RE, config.project, "project")
        _check(_LOCATION_RE, config.location, "location", _MAX_LOCATION_CHARS)
    return replace(config, model=str(model))


def _truthy(value: str | None) -> bool:
    return value is not None and value.lower() in ("true", "1")


def _pick(
    overrides: Mapping[str, str | None],
    source: Mapping[str, str],
    name: str,
    *env_names: str,
) -> str | None:
    value = overrides.get(name)
    if value:
        return value
    for env_name in env_names:
        candidate = source.get(env_name)
        if candidate:
            return candidate
    return None


def resolve_config(
    model: str,
    env: Mapping[str, str] | None = None,
    **overrides: str | None,
) -> GeminiConfig:
    """Resolve a :class:`GeminiConfig` from overrides and google-genai environment variables.

    ``GOOGLE_GENAI_USE_ENTERPRISE``, else ``GOOGLE_GENAI_USE_VERTEXAI``, selects Vertex when
    its lower-cased value is ``true`` or ``1``; the enterprise variable wins when both are set.
    The API key comes from ``GOOGLE_API_KEY``, else ``GEMINI_API_KEY``. Vertex reads
    ``GOOGLE_CLOUD_PROJECT`` and ``GOOGLE_CLOUD_LOCATION`` (default ``global``). Empty values
    count as unset and keyword overrides (``backend``, ``project``, ``location``, ``api_key``,
    ``api_version``) beat the environment.

    Raises:
        GeminiError: ``config`` code for missing (all reported at once) or invalid settings.
    """
    unknown = sorted(set(overrides) - _OVERRIDE_KEYS)
    if unknown:
        raise GeminiError("config", "unknown override: " + ", ".join(unknown)[:100])
    source: Mapping[str, str] = os.environ if env is None else env
    enterprise = source.get("GOOGLE_GENAI_USE_ENTERPRISE")
    flag = enterprise if enterprise is not None else source.get("GOOGLE_GENAI_USE_VERTEXAI")
    requested = overrides.get("backend")
    backend: Backend
    if not requested:
        backend = "vertex" if _truthy(flag) else "ai_studio"
    elif requested == "vertex":
        backend = "vertex"
    elif requested == "ai_studio":
        backend = "ai_studio"
    else:
        raise GeminiError("config", "invalid backend")
    version = _pick(overrides, source, "api_version")
    if backend == "vertex":
        location = _pick(overrides, source, "location", "GOOGLE_CLOUD_LOCATION")
        config = GeminiConfig(
            backend="vertex",
            model=model,
            project=_pick(overrides, source, "project", "GOOGLE_CLOUD_PROJECT"),
            location=location or DEFAULT_LOCATION,
            api_version=version or "v1",
        )
    else:
        config = GeminiConfig(
            backend="ai_studio",
            model=model,
            project=None,
            location=None,
            api_version=version or "v1beta",
            api_key=_pick(overrides, source, "api_key", "GOOGLE_API_KEY", "GEMINI_API_KEY"),
        )
    return validate_config(config)


def vertex_host(location: str) -> str:
    """Return the Vertex AI host for an already validated ``location``."""
    if location == DEFAULT_LOCATION:
        return "aiplatform.googleapis.com"
    if location in ("us", "eu"):
        return f"aiplatform.{location}.rep.googleapis.com"
    return f"{location}-aiplatform.googleapis.com"


def endpoint(config: GeminiConfig) -> str:
    """Return the generateContent URL for a validated ``config``."""
    suffix = f"models/{config.model}:generateContent"
    if config.backend == "ai_studio":
        return f"https://{AI_STUDIO_HOST}/{config.api_version}/{suffix}"
    location = config.location or DEFAULT_LOCATION
    host = vertex_host(location)
    path = f"projects/{config.project}/locations/{location}/publishers/google"
    return f"https://{host}/{config.api_version}/{path}/{suffix}"
