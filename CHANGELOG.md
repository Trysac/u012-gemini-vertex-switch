# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add `GeminiClient`, `GeminiConfig`, `resolve_config` and `GenerateResult`: one Gemini generateContent client for AI Studio and Vertex AI with google-genai environment rules, validated URL parts, injectable transport and token provider, typed `GeminiError`, and `RecordedLLM`/`FakeLLM` test doubles.
- Initial project structure from the factory utility template.
