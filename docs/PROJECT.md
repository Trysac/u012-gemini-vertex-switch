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
| Tokens (input / output) | pending measurement |
| Hours (human) | pending measurement |
| Cost (USD) | pending measurement |
