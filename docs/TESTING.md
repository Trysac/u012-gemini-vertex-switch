# Testing

## Running

```sh
uv run pytest --cov=gemini_vertex_switch   # tests with coverage report
uv run python scripts/check.py      # every gate, as CI and the factory run it
```

## Policy

- Branch coverage of `src/gemini_vertex_switch` must stay at or above 80 %; the gate fails below it.
- Tests exercise the public API (`import gemini_vertex_switch`) and assert return values, raised exceptions and their codes.
- Tests are deterministic: they use an injected transport, no network.

## Layout

`tests/test_<module>.py` mirrors each public module. Shared fixtures go in `tests/conftest.py`. The repository's test files are listed in the repository tree; this document does not enumerate them further.
