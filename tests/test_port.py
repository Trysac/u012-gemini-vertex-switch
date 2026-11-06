from __future__ import annotations

import pytest

from gemini_vertex_switch import FakeLLM, RecordedLLM, RecordingExhaustedError

HELLO = [{"role": "user", "content": "hello"}]


def test_recorded_llm_returns_replies_in_order_and_records_calls():
    llm = RecordedLLM(["one", "two"])
    assert llm.complete(HELLO, max_tokens=5) == "one"
    assert llm.complete(HELLO, max_tokens=5) == "two"
    assert llm.calls == [HELLO, HELLO]


def test_recorded_llm_raises_when_exhausted_and_still_records_the_call():
    llm = RecordedLLM(["only"])
    llm.complete(HELLO, max_tokens=5)
    with pytest.raises(RecordingExhaustedError) as info:
        llm.complete(HELLO, max_tokens=5)
    assert info.value.code == "recording_exhausted"
    assert len(llm.calls) == 2


def test_recorded_llm_snapshots_messages():
    messages = [{"role": "user", "content": "a"}]
    llm = RecordedLLM(["x"])
    llm.complete(messages, max_tokens=5)
    messages[0]["content"] = "changed"
    assert llm.calls[0][0]["content"] == "a"


def test_fake_llm_returns_function_result_and_records_calls():
    llm = FakeLLM(lambda messages: messages[-1]["content"].upper())
    assert llm.complete(HELLO, max_tokens=5) == "HELLO"
    assert llm.calls == [HELLO]


def test_recorded_calls_are_capped():
    llm = FakeLLM(lambda messages: "ok", max_calls=2)
    for index in range(4):
        llm.complete([{"role": "user", "content": str(index)}], max_tokens=5)
    assert [call[0]["content"] for call in llm.calls] == ["2", "3"]
