# Resolve the Gemini backend with google-genai environment rules behind injectable transport and token provider

Status: accepted (generated, pending human review)

## Context

Gemini is served by AI Studio (API key, v1beta) and Vertex AI (project, location, OAuth bearer token, v1) with different hosts, headers and environment variables. Code written for one backend breaks on the other, URL parts built from configuration can be abused (the Vertex location is part of the host name) and tests should not hit the network. The official google-genai SDK can switch backends but is large and hard to fake.

## Decision

Implement a small standard-library client. resolve_config follows the google-genai environment rules (enterprise flag beats the Vertex flag, GOOGLE_API_KEY before GEMINI_API_KEY, empty values unset, location default global) and returns an immutable GeminiConfig that excludes the key from repr. Every URL part is validated with re.fullmatch before a URL is built. HTTP goes through a Transport protocol whose default urllib adapter refuses redirects, accepts https only and bounds reads; Vertex tokens come from an injected token_provider called per request. Errors share one GeminiError with a stable code, and key or token values are redacted from api_message.

## Consequences

The library has no runtime dependencies and is fully testable with fakes and no network. Callers must supply a token_provider (for example from google-auth) for Vertex and cannot use Vertex express-mode keys, streaming, tools, files or embeddings. Validation is stricter than the server, so unusual but legal model names are rejected with a config error. Because secrets are redacted only by exact match, a server that echoes a transformed secret would not be masked.
