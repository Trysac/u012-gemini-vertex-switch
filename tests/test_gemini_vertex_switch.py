"""Behavior tests for the public API of gemini_vertex_switch."""

from __future__ import annotations

import pytest

import gemini_vertex_switch


def test_normalize_trims_and_lowercases() -> None:
    assert gemini_vertex_switch.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        gemini_vertex_switch.normalize(value)


def test_version_is_semver() -> None:
    parts = gemini_vertex_switch.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
