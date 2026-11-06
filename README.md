# gemini-vertex-switch

[![PyPI version](https://img.shields.io/pypi/v/trysac-gemini-vertex-switch)](https://pypi.org/project/trysac-gemini-vertex-switch/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-gemini-vertex-switch)](LICENSE)
[![CI](https://github.com/Trysac/u012-gemini-vertex-switch/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u012-gemini-vertex-switch/actions/workflows/ci.yml)

One Gemini generateContent client that targets AI Studio or Vertex AI from config or google-genai environment variables, with validated URL parts and injectable transport

## Problem

Gemini is reachable through AI Studio with an API key and through Vertex AI with a project,
location and OAuth token, and the endpoints, headers and environment variables differ. Code written
for one backend breaks on the other, URL parts built from config can be abused, and tests hit the
network. This library resolves the backend with the same environment rules as the official
google-genai SDK, builds validated requests and keeps transport and tokens behind injectable
callables.

## Install

```sh
pip install trysac-gemini-vertex-switch
# or
uv add trysac-gemini-vertex-switch
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
from gemini_vertex_switch import GeminiClient, GeminiError, resolve_config

config = resolve_config(
    "gemini-2.5-flash",
    env={"GOOGLE_GENAI_USE_VERTEXAI": "true", "GOOGLE_CLOUD_PROJECT": "my-proj-123"},
)
client = GeminiClient(config, token_provider=lambda: "oauth-token")

try:
    text = client.complete(
        [
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": "Say hi."},
        ],
        max_tokens=64,
    )
    print(text)
except GeminiError as exc:
    print(f"failed: {exc.code}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
