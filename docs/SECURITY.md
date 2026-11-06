# Security

`trysac-gemini-vertex-switch` sends prompts and credentials to Google endpoints. Its defences are: no runtime dependencies, validated URL parts, secrets that never reach logs, errors or events, and a transport that does not follow redirects.

## Threat model

### Defended

- **Key leakage through repr or errors**: `GeminiConfig.api_key` is excluded from `repr`; `repr(GeminiClient)` shows only the config and timeout. `GeminiError.api_message` replaces every occurrence of the key or token with `***` and is cut to 200 characters.
- **Key leakage through events**: `on_event` receives only `backend`, `model`, `status`, `prompt_tokens` and `output_tokens`.
- **Key in URL**: the AI Studio key is sent only in the `x-goog-api-key` header.
- **Header injection**: keys and tokens must be 1 to 4096 printable ASCII characters without whitespace; invalid values are rejected.
- **Host injection**: `location` is part of the Vertex hostname and is validated with `re.fullmatch` (`^[a-z]+(-[a-z0-9]+)*$` or `global`, at most 63 characters). Values such as `evil.example/x` raise a `config` error before any transport call.
- **Path injection**: `model` must match `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$` after an optional `models/` prefix is stripped; `project` must match the Google Cloud project ID pattern. A trailing newline never passes `fullmatch`.
- **Credential forwarding on redirect**: the default transport uses an opener that refuses redirects; a 3xx reply is returned and raised as an `http` error. The default transport accepts only `https://` URLs.
- **Unbounded responses**: the default transport reads at most `max_response_bytes + 1` bytes (default limit 10 MiB); larger bodies raise `response_too_large`.
- **Oversized requests**: request bodies over 4 MiB raise a `config` error.
- **Token provider failures**: a failing `token_provider` raises a `config` error without its original message.
- **Logging of content**: the library never logs prompts, replies, keys or tokens. It uses `logging.getLogger(__name__)` with a `NullHandler` and never configures logging.
- **Test doubles**: `RecordedLLM` and `FakeLLM` keep at most 1000 recorded calls.

### Not defended

- **Prompt content**: prompts and replies are sent as provided and are not filtered, redacted or scanned.
- **Caller-side secret storage**: the library does not store keys or tokens securely; the caller supplies them through the environment, overrides or a callable.
- **Transport replacement**: a caller-injected `Transport` receives the key or token in its headers and is trusted with them.
- **Deep JSON nesting**: nesting in responses is bounded only by the interpreter recursion limit; exceeding it raises `invalid_response`, but the library does not impose its own depth limit.
- **Server-side trust**: the library does not verify response content beyond structure and types.
- **OAuth flows**: the library has no OAuth implementation; token freshness and refresh are the caller's responsibility.

## Reporting

Report vulnerabilities privately to the maintainer through the repository's security contact.
