# gemini-vertex-switch

[![PyPI version](https://img.shields.io/pypi/v/trysac-gemini-vertex-switch)](https://pypi.org/project/trysac-gemini-vertex-switch/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-gemini-vertex-switch)](LICENSE)
[![CI](https://github.com/Trysac/u012-gemini-vertex-switch/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u012-gemini-vertex-switch/actions/workflows/ci.yml)

One Gemini generateContent client that targets AI Studio or Vertex AI from config or google-genai environment variables, with validated URL parts and injectable transport

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-gemini-vertex-switch
# or
uv add trysac-gemini-vertex-switch
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import gemini_vertex_switch

# normalize() trims surrounding whitespace and lower-cases the text.
print(gemini_vertex_switch.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    gemini_vertex_switch.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
