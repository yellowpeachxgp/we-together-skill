import os

import pytest

from we_together.llm import get_llm_client
from we_together.llm.client import LLMMessage, JSONExtractionError
from we_together.llm.providers.mock import MockLLMClient, parse_json_loose


def test_factory_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("WE_TOGETHER_LLM_PROVIDER", raising=False)
    client = get_llm_client()
    assert client.provider == "mock"


def test_factory_reads_env_provider(monkeypatch):
    monkeypatch.setenv("WE_TOGETHER_LLM_PROVIDER", "mock")
    client = get_llm_client()
    assert client.provider == "mock"


def test_factory_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("WE_TOGETHER_LLM_PROVIDER", "anthropic")
    # explicit mock wins
    client = get_llm_client("mock")
    assert client.provider == "mock"


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm_client("nonexistent_provider")


def test_mock_client_chat_returns_scripted():
    client = MockLLMClient(scripted_responses=["hello", "world"])
    r1 = client.chat([LLMMessage(role="user", content="hi")])
    r2 = client.chat([LLMMessage(role="user", content="hi again")])
    assert r1.content == "hello"
    assert r2.content == "world"


def test_mock_client_chat_default_content():
    client = MockLLMClient(default_content="default-x")
    r = client.chat([LLMMessage(role="user", content="hi")])
    assert r.content == "default-x"


def test_mock_client_chat_json_returns_scripted():
    client = MockLLMClient(scripted_json=[{"identity_candidates": []}])
    payload = client.chat_json(
        [LLMMessage(role="user", content="extract")],
        schema_hint={"identity_candidates": "list[object]"},
    )
    assert payload == {"identity_candidates": []}


def test_mock_client_records_calls():
    client = MockLLMClient()
    client.chat([LLMMessage(role="user", content="hi")])
    client.chat_json([LLMMessage(role="user", content="json")], schema_hint="{}")
    assert len(client.calls) == 2
    assert client.calls[0]["type"] == "chat"
    assert client.calls[1]["type"] == "chat_json"


def test_parse_json_loose_plain():
    assert parse_json_loose('{"a": 1}') == {"a": 1}


def test_parse_json_loose_fenced():
    text = '```json\n{"a": 2}\n```'
    assert parse_json_loose(text) == {"a": 2}


def test_parse_json_loose_with_prose():
    text = 'Here is the answer:\n{"x": "y"}\nThanks.'
    assert parse_json_loose(text) == {"x": "y"}


def test_parse_json_loose_rejects_garbage():
    with pytest.raises(JSONExtractionError):
        parse_json_loose("no json here")
