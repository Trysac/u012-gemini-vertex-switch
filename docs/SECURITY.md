# Security

`trysac-gemini-vertex-switch` sends prompts and credentials to Google endpoints, so it keeps the
security surface small: no runtime dependencies, validated URL parts and secrets that never reach
logs, errors or events.

## Secret handling

- The AI Studio key is sent only in the `x-goog-api-key` header, never in the URL.
- The Vertex OAuth token comes from the injected `token_provider`, is requested for every call
  and is never stored. Plug `google-auth` into that callable; the library has no OAuth flow.
- `GeminiConfig.api_key` is excluded from `repr`. `repr(GeminiClient)` shows only the config.
- Keys and tokens must be 1-4096 printable ASCII characters without whitespace, so header
  injection through a key or token is rejected. A failing `token_provider` is reported as a
  `config` error without the original message.
- `GeminiError.api_message` is the API `error.message` with every occurrence of the key or token
  replaced by `***`, then cut to 200 characters. Every error message is at most 200 characters
  and never contains prompt text.
- `on_event` receives only `backend`, `model`, `status`, `prompt_tokens` and `output_tokens`.
- The library uses `logging.getLogger(__name__)` with a `NullHandler`, never configures logging
  and never logs prompts, replies, keys or tokens.

## Disabled redirects

The default transport builds its urllib opener with a redirect handler that refuses to follow
any redirect, so credentials are never forwarded to another host. A 3xx reply is returned to the
client and raised as an `http` error. The transport accepts only `https://` URLs.

## URL validation

All URL parts are validated with `re.fullmatch` before any URL is built, so a trailing newline
never passes:

| Part | Rule |
|---|---|
| model | `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$` (an optional `models/` prefix is stripped first) |
| project | `^[a-z][a-z0-9-]{4,28}[a-z0-9]$` |
| location | `global` or `^[a-z]+(-[a-z0-9]+)*$`, at most 63 characters |
| api_version | `v1`, `v1beta`, `v1alpha` style identifiers |

The location is part of the Vertex host name, so this validation blocks host injection such as
`evil.example/x`. Invalid values raise a `config` error before any transport call.

## Size limits

- Responses: `max_response_bytes` (default 10 MiB). The default transport reads at most
  `max_response_bytes + 1` bytes; larger bodies raise `response_too_large`.
- Requests: bodies over 4 MiB are rejected with a `config` error.
- JSON nesting in responses is bounded by the interpreter recursion limit; exceeding it raises
  `invalid_response`.
- The test doubles keep at most 1000 recorded calls.

## Out of scope

Streaming, tools, files, embeddings, Vertex express-mode keys and OAuth flows.
