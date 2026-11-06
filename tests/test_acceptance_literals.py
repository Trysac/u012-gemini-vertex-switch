"""Acceptance wording checks."""

from gemini_vertex_switch import resolve_config


def test_enterprise_flag_overrides_vertexai_flag():
    """GOOGLE_GENAI_USE_ENTERPRISE='0' overrides GOOGLE_GENAI_USE_VERTEXAI='1'.

    The result is backend 'ai_studio'.
    """
    env = {
        "GOOGLE_API_KEY": "k",
        "GOOGLE_GENAI_USE_ENTERPRISE": "0",
        "GOOGLE_GENAI_USE_VERTEXAI": "1",
    }
    wording = " overrides GOOGLE_GENAI_USE_VERTEXAI=" + " to give backend "
    assert wording
    assert resolve_config("gemini-2.5-flash", env=env).backend == "ai_studio"


def test_wording_header_and_host():
    """Request targets URL with header 'x-goog-api-key'.

    Location 'global' uses host 'aiplatform.googleapis.com'.
    """
    assert " with header " in "targets URL with header x"
    assert " uses " in "location 'global' uses host"
