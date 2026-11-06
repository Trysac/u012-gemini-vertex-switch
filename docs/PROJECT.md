# Project record

## Objective

Provide one zero-dependency Gemini generateContent client that switches between AI Studio and Vertex AI using google-genai environment rules, validates URL parts before any request, and keeps transport and tokens injectable so tests never touch the network.

## Scope

- In scope: backend resolution from config or environment, request encoding for `complete` and `generate`, response parsing with typed errors, injectable `Transport` and `token_provider`, and the `LLMPort` with deterministic test doubles.
- Out of scope: streaming, tools, files, embeddings, Vertex express-mode keys and OAuth flows. A caller may plug google-auth into `token_provider`.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | 379609 / 85986 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.7286 |

## Factory run u012 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | claude-sonnet-5-5 | yes | 2947 | 71875 | 0 | 4246 | 0.3627 |
| fix-1 | claude-sonnet-5-5 | no | 6 | 1898 | 10937 | 45233 | 0.0509 |
| fix-2 | claude-sonnet-5-5 | no | 6 | 1294 | 7347 | 40523 | 0.0354 |
| fix-3 | claude-sonnet-5-5 | no | 6 | 779 | 7388 | 41157 | 0.0304 |
| audit | claude-sonnet-5-5 | no | 10 | 3234 | 37658 | 90937 | 0.1356 |
| fix-4 | claude-sonnet-5-5 | no | 6 | 1722 | 9196 | 42103 | 0.0444 |
| docs | claude-haiku-5-5 | no | 112429 | 5184 | 0 | 0 | 0.0692 |

Total: $0.7286. Prices: Anthropic list prices.
