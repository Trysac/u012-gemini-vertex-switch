from __future__ import annotations

import json

import pytest

from gemini_vertex_switch import (
    GeminiClient,
    GeminiConfig,
    GeminiError,
    GenerateResult,
    LLMPort,
    resolve_config,
)
from gemini_vertex_switch.transport import UrllibTransport

KEY = "sentinel-key-value"
TOKEN = "sentinel-token-value"
MODEL = "gemini-2.5-flash"
AI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
VERTEX_URL = "https://us-central1-aiplatform.googleapis.com/v1/projects/my-proj-123/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent"  # noqa: E501
GLOBAL_URL = "https://aiplatform.googleapis.com/v1/projects/my-proj-123/locations/global/publishers/google/models/gemini-2.5-flash:generateContent"  # noqa: E501
US_URL = "https://aiplatform.us.rep.googleapis.com/v1/projects/my-proj-123/locations/us/publishers/google/models/gemini-2.5-flash:generateContent"  # noqa: E501

USER_HI = [{"role": "user", "content": "hi"}]


class FakeTransport:
    """Records requests and replays canned responses."""

    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def post(self, url, headers, body, timeout):
        call = {
            "url": url,
            "headers": dict(headers),
            "body": body,
            "timeout": timeout,
        }
        self.calls.append(call)
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def reply(text="hello", **extra):
    payload = {
        "candidates": [
            {
                "content": {"role": "model", "parts": [{"text": text}]},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 5},
    }
    payload.update(extra)
    return 200, json.dumps(payload).encode()


def ai_config(**overrides):
    return resolve_config(MODEL, env={"GOOGLE_API_KEY": KEY}, **overrides)


def vertex_config(location="us-central1"):
    return resolve_config(
        MODEL,
        env={
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
            "GOOGLE_CLOUD_PROJECT": "my-proj-123",
            "GOOGLE_CLOUD_LOCATION": location,
        },
    )


def vertex_client(transport, location="us-central1", provider=lambda: "tok", **kwargs):
    return GeminiClient(
        vertex_config(location),
        transport=transport,
        token_provider=provider,
        **kwargs,
    )


# ---------------------------------------------------------------- resolve_config


def test_vertex_from_env_defaults_to_global_location():
    config = resolve_config(
        "gemini-2.5-flash",
        env={"GOOGLE_GENAI_USE_VERTEXAI": "TRUE", "GOOGLE_CLOUD_PROJECT": "my-proj-123"},
    )
    assert config.backend == "vertex"
    assert config.location == "global"
    assert config.project == "my-proj-123"
    assert config.api_version == "v1"
    assert config.api_key is None


def test_enterprise_flag_overrides_vertexai_flag():
    config = resolve_config(
        "gemini-2.5-flash",
        env={
            "GOOGLE_API_KEY": KEY,
            "GOOGLE_GENAI_USE_ENTERPRISE": "0",
            "GOOGLE_GENAI_USE_VERTEXAI": "1",
        },
    )
    assert config.backend == "ai_studio"
    assert config.api_version == "v1beta"
    assert config.api_key == KEY
    assert config.project is None
    assert config.location is None


def test_enterprise_flag_true_selects_vertex_even_when_vertexai_is_false():
    config = resolve_config(
        MODEL,
        env={
            "GOOGLE_GENAI_USE_ENTERPRISE": "1",
            "GOOGLE_GENAI_USE_VERTEXAI": "false",
            "GOOGLE_CLOUD_PROJECT": "my-proj-123",
        },
    )
    assert config.backend == "vertex"


def test_non_true_flag_values_select_ai_studio():
    env = {"GOOGLE_GENAI_USE_VERTEXAI": "yes", "GOOGLE_API_KEY": KEY}
    assert resolve_config(MODEL, env=env).backend == "ai_studio"


def test_google_api_key_beats_gemini_api_key():
    env = {"GOOGLE_API_KEY": "google-key", "GEMINI_API_KEY": "gemini-key"}
    assert resolve_config(MODEL, env=env).api_key == "google-key"


def test_empty_google_api_key_counts_as_unset():
    env = {"GOOGLE_API_KEY": "", "GEMINI_API_KEY": "gemini-key"}
    assert resolve_config(MODEL, env=env).api_key == "gemini-key"


def test_resolve_config_reads_process_environment_by_default(monkeypatch):
    for name in (
        "GOOGLE_GENAI_USE_ENTERPRISE",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GEMINI_API_KEY",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", KEY)
    assert resolve_config(MODEL).api_key == KEY


def test_vertex_without_project_reports_missing_project():
    with pytest.raises(GeminiError) as info:
        resolve_config(MODEL, env={"GOOGLE_GENAI_USE_VERTEXAI": "true"})
    assert info.value.code == "config"
    assert info.value.missing == ["GOOGLE_CLOUD_PROJECT"]


def test_ai_studio_without_key_reports_missing_key():
    with pytest.raises(GeminiError) as info:
        resolve_config(MODEL, env={})
    assert info.value.code == "config"
    assert info.value.missing == ["GOOGLE_API_KEY"]


def test_overrides_beat_environment():
    config = resolve_config(
        MODEL,
        env={
            "GOOGLE_API_KEY": "env-key",
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
            "GOOGLE_CLOUD_PROJECT": "env-project-1",
        },
        backend="ai_studio",
        api_key=KEY,
        api_version="v1alpha",
    )
    assert config.backend == "ai_studio"
    assert config.api_key == KEY
    assert config.api_version == "v1alpha"
    vertex = resolve_config(
        MODEL,
        env={"GOOGLE_CLOUD_PROJECT": "env-project-1", "GOOGLE_CLOUD_LOCATION": "eu"},
        backend="vertex",
        project="my-proj-123",
        location="asia-east1",
    )
    assert (vertex.project, vertex.location) == ("my-proj-123", "asia-east1")


def test_models_prefix_is_stripped():
    assert ai_config().model == MODEL
    config = resolve_config("models/gemini-2.5-flash", env={"GOOGLE_API_KEY": KEY})
    assert config.model == MODEL


def test_unknown_override_and_invalid_backend_are_rejected():
    with pytest.raises(GeminiError) as unknown:
        resolve_config(MODEL, env={"GOOGLE_API_KEY": KEY}, colour="red")
    assert unknown.value.code == "config"
    with pytest.raises(GeminiError) as backend:
        resolve_config(MODEL, env={"GOOGLE_API_KEY": KEY}, backend="gcp")
    assert backend.value.code == "config"


@pytest.mark.parametrize(
    "location",
    [
        "evil.example/x",
        "us-central1\n",
        "US",
        "us_central1",
        "us-",
        "-us",
        "a" * 64,
        "x@evil.example",
    ],
)
def test_invalid_location_rejected_before_any_transport_call(location):
    with pytest.raises(GeminiError) as via_resolve:
        resolve_config(
            MODEL,
            env={"GOOGLE_CLOUD_PROJECT": "my-proj-123"},
            backend="vertex",
            location=location,
        )
    assert via_resolve.value.code == "config"
    transport = FakeTransport()
    config = GeminiConfig("vertex", MODEL, "my-proj-123", location, "v1")
    with pytest.raises(GeminiError) as via_client:
        GeminiClient(config, transport=transport, token_provider=lambda: "tok")
    assert via_client.value.code == "config"
    assert transport.calls == []


@pytest.mark.parametrize(
    "model",
    [
        "a/../b",
        "models/",
        "models/a/../b",
        "-a",
        "a b",
        "a\n",
        "a:b",
        "x" * 129,
        "",
    ],
)
def test_invalid_model_rejected_before_any_transport_call(model):
    with pytest.raises(GeminiError) as via_resolve:
        resolve_config(model, env={"GOOGLE_API_KEY": KEY})
    assert via_resolve.value.code == "config"
    transport = FakeTransport()
    with pytest.raises(GeminiError) as via_client:
        GeminiClient(GeminiConfig("ai_studio", model, None, None, "v1beta", KEY), transport=transport)
    assert via_client.value.code == "config"
    assert transport.calls == []


def test_non_string_model_is_rejected():
    config = GeminiConfig("ai_studio", 123, None, None, "v1beta", KEY)  # type: ignore[arg-type]
    with pytest.raises(GeminiError) as info:
        GeminiClient(config)
    assert info.value.code == "config"


@pytest.mark.parametrize("project", ["Bad_Project", "short", "my-proj-123\n", "1-starts-digit", "p" * 40])
def test_invalid_project_is_rejected(project):
    with pytest.raises(GeminiError) as info:
        resolve_config(MODEL, env={"GOOGLE_CLOUD_PROJECT": project}, backend="vertex")
    assert info.value.code == "config"


@pytest.mark.parametrize("api_key", ["bad key", "key\r\nX-Evil: 1", "k" * 5000, "key\n"])
def test_invalid_api_key_is_rejected_without_echoing_it(api_key):
    with pytest.raises(GeminiError) as info:
        resolve_config(MODEL, env={}, api_key=api_key)
    assert info.value.code == "config"
    assert "key" not in str(info.value).replace("api_key", "")


@pytest.mark.parametrize("version", ["v1/../x", "1", "v1\n", "latest"])
def test_invalid_api_version_is_rejected(version):
    with pytest.raises(GeminiError) as info:
        ai_config(api_version=version)
    assert info.value.code == "config"


# ---------------------------------------------------------------- client: requests


def test_ai_studio_request_url_and_key_header():
    transport = FakeTransport(reply())
    client = GeminiClient(ai_config(), transport=transport)
    client.complete(USER_HI, max_tokens=8)
    call = transport.calls[0]
    assert call["url"] == AI_URL
    assert call["headers"]["x-goog-api-key"] == KEY
    assert KEY not in call["url"]
    assert "Authorization" not in call["headers"]
    assert call["timeout"] == 60.0


def test_vertex_request_url_and_bearer_header():
    transport = FakeTransport(reply())
    client = vertex_client(transport)
    client.complete(USER_HI, max_tokens=8)
    call = transport.calls[0]
    assert call["url"] == VERTEX_URL
    assert call["headers"]["Authorization"] == "Bearer tok"
    assert "x-goog-api-key" not in call["headers"]


def test_vertex_global_and_multi_region_hosts():
    transport = FakeTransport(reply(), reply(), reply())
    vertex_client(transport, location="global").complete(USER_HI, max_tokens=8)
    vertex_client(transport, location="us").complete(USER_HI, max_tokens=8)
    vertex_client(transport, location="eu").complete(USER_HI, max_tokens=8)
    urls = [call["url"] for call in transport.calls]
    assert urls[0] == GLOBAL_URL
    assert urls[1] == US_URL
    assert urls[2].startswith("https://aiplatform.eu.rep.googleapis.com/v1/projects/")


def test_token_provider_is_called_for_every_request():
    tokens = iter(["tok-1", "tok-2"])
    transport = FakeTransport(reply(), reply())
    client = vertex_client(transport, provider=lambda: next(tokens))
    client.complete(USER_HI, max_tokens=8)
    client.complete(USER_HI, max_tokens=8)
    sent = [call["headers"]["Authorization"] for call in transport.calls]
    assert sent == ["Bearer tok-1", "Bearer tok-2"]


def test_complete_maps_roles_and_max_tokens():
    transport = FakeTransport(reply("joined text"))
    client = GeminiClient(ai_config(), transport=transport)
    messages = [
        {"role": "system", "content": "Be brief"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    assert client.complete(messages, max_tokens=64) == "joined text"
    sent = json.loads(transport.calls[0]["body"])
    assert sent == {
        "systemInstruction": {"parts": [{"text": "Be brief"}]},
        "contents": [
            {"role": "user", "parts": [{"text": "hi"}]},
            {"role": "model", "parts": [{"text": "hello"}]},
        ],
        "generationConfig": {"maxOutputTokens": 64},
    }


def test_multiple_system_messages_are_joined_and_none_is_omitted():
    transport = FakeTransport(reply(), reply())
    client = GeminiClient(ai_config(), transport=transport)
    system = [{"role": "system", "content": "a"}, {"role": "system", "content": "b"}]
    client.complete([*system, *USER_HI], max_tokens=8)
    client.complete(USER_HI, max_tokens=8)
    first = json.loads(transport.calls[0]["body"])
    second = json.loads(transport.calls[1]["body"])
    assert first["systemInstruction"]["parts"][0]["text"] == "a\n\nb"
    assert "systemInstruction" not in second


def test_response_text_parts_are_joined_and_thoughts_skipped():
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "plan", "thought": True},
                        {"text": "Hel"},
                        {"functionCall": {"name": "f"}},
                        {"text": "lo"},
                    ]
                }
            }
        ]
    }
    transport = FakeTransport((200, json.dumps(payload).encode()))
    client = GeminiClient(ai_config(), transport=transport)
    assert client.complete(USER_HI, max_tokens=8) == "Hello"


def test_generate_returns_structured_result():
    transport = FakeTransport(reply("ok"))
    client = GeminiClient(ai_config(), transport=transport)
    contents = [{"role": "user", "parts": [{"text": "hi"}]}]
    result = client.generate(
        contents,
        system_instruction="be brief",
        generation_config={"temperature": 0.2},
    )
    sent = json.loads(transport.calls[0]["body"])
    assert sent == {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": "be brief"}]},
        "generationConfig": {"temperature": 0.2},
    }
    assert isinstance(result, GenerateResult)
    assert result.text == "ok"
    assert result.finish_reason == "STOP"
    assert result.prompt_tokens == 3
    assert result.output_tokens == 5
    assert "candidates" in result.raw
    assert "raw" not in repr(result)


def test_generate_without_optional_arguments():
    transport = FakeTransport(reply())
    client = GeminiClient(ai_config(), transport=transport)
    client.generate([{"role": "user", "parts": [{"text": "hi"}]}], system_instruction="")
    sent = json.loads(transport.calls[0]["body"])
    assert set(sent) == {"contents"}


def test_candidate_without_content_gives_empty_text_and_bad_usage_is_none():
    payload = {"candidates": [{"finishReason": 7}], "usageMetadata": {"promptTokenCount": True}}
    transport = FakeTransport((200, json.dumps(payload).encode()))
    result = GeminiClient(ai_config(), transport=transport).generate(
        [{"role": "user", "parts": []}]
    )
    assert result.text == ""
    assert result.finish_reason is None
    assert result.prompt_tokens is None
    assert result.output_tokens is None


def test_candidate_with_content_but_no_parts_gives_empty_text():
    payload = {"candidates": [{"content": {"role": "model"}}], "usageMetadata": "nope"}
    transport = FakeTransport((200, json.dumps(payload).encode()))
    client = GeminiClient(ai_config(), transport=transport)
    assert client.complete(USER_HI, max_tokens=8) == ""


# ---------------------------------------------------------------- client: config errors


def test_vertex_client_without_token_provider_is_a_config_error():
    with pytest.raises(GeminiError) as info:
        GeminiClient(vertex_config())
    assert info.value.code == "config"
    assert info.value.missing == ["token_provider"]


def test_direct_config_reports_every_missing_setting_at_once():
    with pytest.raises(GeminiError) as vertex:
        GeminiClient(GeminiConfig("vertex", MODEL, None, None, "v1"))
    assert vertex.value.missing == [
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "token_provider",
    ]
    with pytest.raises(GeminiError) as studio:
        GeminiClient(GeminiConfig("ai_studio", MODEL, None, None, "v1beta"))
    assert studio.value.missing == ["GOOGLE_API_KEY"]


def test_direct_config_with_unknown_backend_is_rejected():
    with pytest.raises(GeminiError) as info:
        GeminiClient(GeminiConfig("gcp", MODEL, None, None, "v1", KEY))  # type: ignore[arg-type]
    assert info.value.code == "config"


@pytest.mark.parametrize("timeout", [0, -1, True, "60"])
def test_invalid_timeout_is_rejected(timeout):
    with pytest.raises(GeminiError) as info:
        GeminiClient(ai_config(), timeout=timeout)
    assert info.value.code == "config"


@pytest.mark.parametrize("limit", [0, -5, True, 1.5])
def test_invalid_max_response_bytes_is_rejected(limit):
    with pytest.raises(GeminiError) as info:
        GeminiClient(ai_config(), max_response_bytes=limit)
    assert info.value.code == "config"


def test_default_transport_is_the_urllib_adapter():
    client = GeminiClient(ai_config())
    assert isinstance(client._transport, UrllibTransport)
    assert LLMPort in GeminiClient.__mro__


def test_token_provider_failures_become_config_errors_without_leaking():
    def boom() -> str:
        raise RuntimeError(TOKEN)

    client = vertex_client(FakeTransport(), provider=boom)
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert info.value.code == "config"
    assert TOKEN not in str(info.value)
    assert info.value.__cause__ is None


@pytest.mark.parametrize("token", ["bad token", "", "tok\nX: y", None, 5])
def test_invalid_tokens_are_rejected(token):
    transport = FakeTransport()
    client = vertex_client(transport, provider=lambda: token)
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert info.value.code == "config"
    assert transport.calls == []


@pytest.mark.parametrize("max_tokens", [0, -1, True, 1.5, "8"])
def test_invalid_max_tokens_is_rejected(max_tokens):
    transport = FakeTransport()
    client = GeminiClient(ai_config(), transport=transport)
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=max_tokens)
    assert info.value.code == "config"
    assert transport.calls == []


@pytest.mark.parametrize(
    "messages",
    [
        "hello",
        b"hello",
        [],
        [{"role": "system", "content": "only system"}],
        [{"role": "tool", "content": "x"}],
        [{"role": "user", "content": 5}],
        [{"content": "no role"}],
        ["not a mapping"],
        42,
    ],
)
def test_invalid_messages_are_rejected(messages):
    transport = FakeTransport()
    client = GeminiClient(ai_config(), transport=transport)
    with pytest.raises(GeminiError) as info:
        client.complete(messages, max_tokens=8)
    assert info.value.code == "config"
    assert transport.calls == []


@pytest.mark.parametrize(
    ("contents", "kwargs"),
    [
        ([], {}),
        ("text", {}),
        ([1], {}),
        ([{"role": "user", "parts": [{"text": "x"}]}], {"system_instruction": 5}),
        ([{"role": "user", "parts": [{"text": "x"}]}], {"generation_config": "nope"}),
        ([{"role": object()}], {}),
        ([{"text": "\ud800"}], {}),
        ([{"text": "a" * 4_194_305}], {}),
    ],
)
def test_invalid_generate_input_is_rejected(contents, kwargs):
    transport = FakeTransport()
    client = GeminiClient(ai_config(), transport=transport)
    with pytest.raises(GeminiError) as info:
        client.generate(contents, **kwargs)
    assert info.value.code == "config"
    assert transport.calls == []


# ---------------------------------------------------------------- client: response errors


def test_http_400_raises_http_error_with_status_and_api_message():
    body = {"error": {"code": 400, "message": "API key not valid"}}
    client = GeminiClient(ai_config(), transport=FakeTransport((400, json.dumps(body).encode())))
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert info.value.code == "http"
    assert info.value.status == 400
    assert info.value.api_message == "API key not valid"


def test_api_message_is_redacted_and_truncated_to_200_characters():
    message = f"bad {KEY} " + "x" * 500
    body = json.dumps({"error": {"message": message}}).encode()
    client = GeminiClient(ai_config(), transport=FakeTransport((500, body)))
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    expected = ("bad *** " + "x" * 500)[:200]
    assert info.value.api_message == expected
    assert len(info.value.api_message) == 200
    assert len(str(info.value)) <= 200


@pytest.mark.parametrize(
    "body",
    [
        b"<html>gateway</html>",
        b"[1, 2]",
        b'{"error": "plain"}',
        b'{"error": {"message": 5}}',
        b"",
        b"[" * 100_000,
    ],
)
def test_http_error_without_usable_message_has_no_api_message(body):
    client = GeminiClient(ai_config(), transport=FakeTransport((502, body)))
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert info.value.code == "http"
    assert info.value.status == 502
    assert info.value.api_message is None


def test_redirect_status_is_an_http_error_not_followed():
    transport = FakeTransport((302, b""))
    client = GeminiClient(ai_config(), transport=transport)
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert (info.value.code, info.value.status) == ("http", 302)
    assert len(transport.calls) == 1


def test_transport_failures_become_http_errors_without_status():
    client = GeminiClient(ai_config(), transport=FakeTransport(TimeoutError(KEY)))
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert info.value.code == "http"
    assert info.value.status is None
    assert KEY not in str(info.value)


def test_no_candidates_with_block_reason_raises_empty_response():
    body = json.dumps({"promptFeedback": {"blockReason": "SAFETY"}}).encode()
    client = GeminiClient(ai_config(), transport=FakeTransport((200, body)))
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert info.value.code == "empty_response"
    assert info.value.reason == "SAFETY"


@pytest.mark.parametrize(
    "payload",
    [{}, {"candidates": []}, {"candidates": [], "promptFeedback": {"blockReason": 3}}],
)
def test_no_candidates_without_reason(payload):
    client = GeminiClient(ai_config(), transport=FakeTransport((200, json.dumps(payload).encode())))
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert info.value.code == "empty_response"
    assert info.value.reason is None


def test_long_block_reason_is_clipped():
    body = json.dumps({"promptFeedback": {"blockReason": "R" * 500}}).encode()
    client = GeminiClient(ai_config(), transport=FakeTransport((200, body)))
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert len(info.value.reason) == 64


def test_body_over_max_response_bytes_raises_response_too_large():
    transport = FakeTransport((200, b"x" * 11))
    client = GeminiClient(ai_config(), transport=transport, max_response_bytes=10)
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert info.value.code == "response_too_large"


def test_body_exactly_at_the_limit_is_accepted():
    status, body = reply()
    client = GeminiClient(
        ai_config(),
        transport=FakeTransport((status, body)),
        max_response_bytes=len(body),
    )
    assert client.complete(USER_HI, max_tokens=8) == "hello"


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"\xff\xfe",
        b"[1]",
        b"[" * 100_000,
        b'{"candidates": "x"}',
        b'{"candidates": [1]}',
        b'{"candidates": [{"content": "x"}]}',
        b'{"candidates": [{"content": {"parts": "x"}}]}',
        b'{"candidates": [{"content": {"parts": ["x"]}}]}',
    ],
)
def test_malformed_success_bodies_raise_invalid_response(body):
    client = GeminiClient(ai_config(), transport=FakeTransport((200, body)))
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert info.value.code == "invalid_response"


@pytest.mark.parametrize("result", [("200", b"{}"), (200, "{}"), (200, None)])
def test_malformed_transport_results_raise_invalid_response(result):
    client = GeminiClient(ai_config(), transport=FakeTransport(result))
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert info.value.code == "invalid_response"


# ---------------------------------------------------------------- events and secrets


def test_on_event_payload_has_exactly_the_documented_keys():
    events = []
    client = vertex_client(FakeTransport(reply()), on_event=events.append)
    client.complete(USER_HI, max_tokens=8)
    assert events == [
        {
            "backend": "vertex",
            "model": MODEL,
            "status": 200,
            "prompt_tokens": 3,
            "output_tokens": 5,
        }
    ]


def test_on_event_is_emitted_for_http_errors_and_empty_responses():
    events = []
    body = json.dumps({"usageMetadata": {"promptTokenCount": 4}}).encode()
    transport = FakeTransport((429, b"{}"), (200, body))
    client = GeminiClient(ai_config(), transport=transport, on_event=events.append)
    with pytest.raises(GeminiError):
        client.complete(USER_HI, max_tokens=8)
    with pytest.raises(GeminiError):
        client.complete(USER_HI, max_tokens=8)
    assert [e["status"] for e in events] == [429, 200]
    assert events[0]["prompt_tokens"] is None
    assert (events[1]["prompt_tokens"], events[1]["output_tokens"]) == (4, None)


def test_failing_on_event_callback_does_not_break_the_call():
    def boom(event):
        raise RuntimeError("callback failed")

    client = GeminiClient(ai_config(), transport=FakeTransport(reply()), on_event=boom)
    assert client.complete(USER_HI, max_tokens=8) == "hello"


def test_ai_studio_key_never_appears_in_repr_errors_or_events():
    events = []
    body = json.dumps({"error": {"message": f"invalid key {KEY}"}}).encode()
    transport = FakeTransport((400, body), (200, b"x" * 3))
    config = ai_config()
    client = GeminiClient(config, transport=transport, on_event=events.append)
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert info.value.api_message == "invalid key ***"
    texts = [repr(config), repr(client), str(info.value), info.value.api_message, repr(events)]
    assert all(KEY not in text for text in texts)
    assert "api_key" not in repr(config)
    assert transport.calls[0]["headers"]["x-goog-api-key"] == KEY
    with pytest.raises(GeminiError) as invalid:
        client.complete(USER_HI, max_tokens=8)
    assert KEY not in str(invalid.value)


def test_vertex_token_never_appears_in_repr_errors_or_events():
    events = []
    body = json.dumps({"error": {"message": f"token {TOKEN} expired"}}).encode()
    config = vertex_config()
    client = GeminiClient(
        config,
        transport=FakeTransport((401, body)),
        token_provider=lambda: TOKEN,
        on_event=events.append,
    )
    with pytest.raises(GeminiError) as info:
        client.complete(USER_HI, max_tokens=8)
    assert info.value.api_message == "token *** expired"
    texts = [repr(config), repr(client), str(info.value), info.value.api_message, repr(events)]
    assert all(TOKEN not in text for text in texts)
