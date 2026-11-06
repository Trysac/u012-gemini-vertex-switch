# gemini-vertex-switch

[![PyPI version](https://img.shields.io/pypi/v/trysac-gemini-vertex-switch)](https://pypi.org/project/trysac-gemini-vertex-switch/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-gemini-vertex-switch)](LICENSE)
[![CI](https://github.com/Trysac/u012-gemini-vertex-switch/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u012-gemini-vertex-switch/actions/workflows/ci.yml)

One Gemini generateContent client that targets AI Studio or Vertex AI from config or google-genai environment variables, with validated URL parts and injectable transport.

## Problem

Gemini is reachable through AI Studio with an API key and through Vertex AI with a project, location and OAuth token, and the endpoints, headers and environment variables differ. Code written for one backend breaks on the other, URL parts built from config can be abused, and tests hit the network. This library resolves the backend with the same environment rules as the official google-genai SDK, validates every URL part before building a request, and keeps transport and tokens behind injectable callables.

## Install

```sh
pip install trysac-gemini-vertex-switch
# or
uv add trysac-gemini-vertex-switch
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import os
from gemini_vertex_switch import GeminiClient, GeminiError, resolve_config

config = resolve_config("gemini-2.5-flash", env={"GOOGLE_API_KEY": os.environ["GOOGLE_API_KEY"]})
client = GeminiClient(config)

try:
    print(client.complete([{"role": "user", "content": "Say hi"}], max_tokens=32))
except GeminiError as exc:
    print(f"failed: {exc.code}")
```

## Public API

- `resolve_config(model, env=None, **overrides) -> GeminiConfig`: applies google-genai rules. `GOOGLE_GENAI_USE_ENTERPRISE` takes precedence over `GOOGLE_GENAI_USE_VERTEXAI`; a value of `true` or `1` (case-insensitive) selects Vertex. The API key is read from `GOOGLE_API_KEY`, then `GEMINI_API_KEY`. Vertex reads `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` (default `global`). Empty values count as unset; keyword overrides (`backend`, `project`, `location`, `api_key`, `api_version`) beat the environment.
- `GeminiConfig`: frozen dataclass with `backend`, `model`, `project`, `location`, `api_version` (`v1beta` for AI Studio, `v1` for Vertex) and `api_key` (excluded from `repr`).
- `GeminiClient(config, *, transport=None, token_provider=None, timeout=60.0, max_response_bytes=10_485_760, on_event=None)`: `token_provider` is required for Vertex.
- `GeminiClient.complete(messages, *, max_tokens) -> str`: system messages are joined into `systemInstruction`, `assistant` becomes `model`.
- `GeminiClient.generate(contents, *, system_instruction=None, generation_config=None) -> GenerateResult`: raw Gemini request with `text`, `finish_reason`, `prompt_tokens`, `output_tokens` and `raw`.
- `LLMPort`, `Message`, `FakeLLM`, `RecordedLLM`, `RecordingExhaustedError`: port and deterministic test doubles.
- `Transport`: protocol `post(url, headers, body, timeout) -> (status, body)`.
- Errors: `GeminiError` with `code` in `config`, `http`, `empty_response`, `response_too_large`, `invalid_response`, plus `missing`, `status`, `api_message` and `reason` attributes.
- Limits: `model`, `project`, `location` and `api_version` are validated with `re.fullmatch`; request bodies over 4 MiB are rejected; the default transport accepts only `https://` URLs, does not follow redirects and reads at most `max_response_bytes + 1` bytes.
- Event payload for `on_event`: `backend`, `model`, `status`, `prompt_tokens`, `output_tokens`.

See [security notes](docs/SECURITY.md) for the threat model.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
