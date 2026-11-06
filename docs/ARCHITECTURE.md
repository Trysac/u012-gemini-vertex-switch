# Architecture

## Purpose

`trysac-gemini-vertex-switch` is a small, dependency-free Python library that exposes one Gemini generateContent client for AI Studio and Vertex AI, resolves the backend from config or google-genai environment variables, validates URL parts, and accepts an injectable transport and token provider.

## Shape

```text
caller code --> gemini_vertex_switch (public API in __init__.py)
                    |
                    +-- config.py   backend resolution, validation, URL building
                    +-- client.py   GeminiClient: request encoding, HTTP call, response parsing
                    +-- transport.py Transport protocol and UrllibTransport (default)
                    +-- port.py     LLMPort, Message, FakeLLM, RecordedLLM
                    +-- errors.py   GeminiError and clip()
```

- **Public API**: the names listed in `__all__` of `src/gemini_vertex_switch/__init__.py`. Anything else is internal.
- **Errors**: every failure raises `GeminiError` with a stable `code`; the library never prints or exits.
- **Logging**: `logging.getLogger(__name__)` with a `NullHandler`; the library never configures logging.
- **Side effects**: the only I/O is the HTTP call made through the `Transport` object, which is the default urllib adapter unless the caller injects another one.

## Quality contract

The gates are defined in `scripts/check.py`. See [TESTING.md](TESTING.md).

## Decisions

Architecture decisions are recorded in [decisions/](decisions/) as numbered ADRs.
