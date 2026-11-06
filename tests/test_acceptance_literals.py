"""Acceptance checks for backend resolution."""

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
    assert resolve_config("gemini-2.5-flash", env=env).backend == "ai_studio"
