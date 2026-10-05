from io import BytesIO
import json
from urllib.error import HTTPError

import pytest

from patchloop import providers


def test_transport_uses_bearer_and_json(monkeypatch):
    captured = {}

    def open_request(request, timeout):
        captured.update(url=request.full_url, authorization=request.get_header("Authorization"),
                        payload=json.loads(request.data), timeout=timeout)
        return BytesIO(b'{"id":"request-1"}')

    monkeypatch.setattr(providers, "urlopen", open_request)
    assert providers.request_json("https://example.invalid", "test-only", {"hello": "world"}) == {"id": "request-1"}
    assert captured == {"url": "https://example.invalid", "authorization": "Bearer test-only",
                        "payload": {"hello": "world"}, "timeout": 60}


def test_error_does_not_echo_secret_or_provider_body(monkeypatch):
    def fail(request, timeout):
        raise HTTPError(request.full_url, 401, "secret-key", {}, BytesIO(b"secret-key"))

    monkeypatch.setattr(providers, "urlopen", fail)
    with pytest.raises(providers.ProviderError, match="^Provider HTTP 401$"):
        providers.request_json("https://example.invalid", "secret-key")


def test_missing_credentials_fail_explicitly(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    with pytest.raises(providers.ProviderError, match="NEBIUS_API_KEY"):
        providers.NebiusClient()


def test_model_completion_records_usage_and_truncation(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-only")
    response = {"id": "req", "model": "nvidia/test-nemotron",
                "choices": [{"finish_reason": "stop", "message": {"content": "Allow owned resources."}}],
                "usage": {"total_tokens": 12}}
    monkeypatch.setattr(providers, "request_json", lambda *args: response)
    client = providers.NebiusClient()
    assert client.complete([], model="nvidia/test-nemotron")["usage"]["total_tokens"] == 12
    response["choices"][0]["finish_reason"] = "length"
    with pytest.raises(providers.ProviderError, match="did not finish"):
        client.complete([], model="nvidia/test-nemotron")


def test_guidance_must_contain_real_results(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-only")
    monkeypatch.setattr(providers, "request_json", lambda *args: {"results": []})
    with pytest.raises(providers.ProviderError, match="no guidance"):
        providers.TavilyClient().guidance()
    monkeypatch.setattr(providers, "request_json", lambda *args: {
        "request_id": "req", "results": [{"url": "https://cheatsheetseries.owasp.org/",
                                             "title": "Authorization", "content": "Deny by default."}],
    })
    result = providers.TavilyClient().guidance()
    assert result["request_id"] == "req"
    assert result["trust"].startswith("untrusted")


def test_native_chat_preserves_function_calls_and_rejects_bad_envelopes(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-only")
    call = {"type": "function", "id": "c1", "function": {
        "name": "get_user_details", "arguments": '{"user_id":"fixture"}'}}
    response = {"choices": [{"finish_reason": "tool_calls", "message": {
        "content": None, "tool_calls": [call]}}], "usage": {"total_tokens": 4}}
    captured = []
    monkeypatch.setattr(providers, "request_json", lambda *args: captured.append(args) or response)
    client = providers.NebiusClient()
    assert client.chat([], model="nvidia/test-nemotron", tools=[])["message"]["tool_calls"] == [call]
    assert captured[0][2]["parallel_tool_calls"] is False
    response["choices"][0]["message"]["tool_calls"].append(call)
    with pytest.raises(providers.ProviderError, match="malformed"):
        client.chat([], model="nvidia/test-nemotron", tools=[])
    response["choices"][0]["message"]["tool_calls"] = [call]
    response["choices"][0]["finish_reason"] = "length"
    with pytest.raises(providers.ProviderError, match="incomplete"):
        client.chat([], model="nvidia/test-nemotron", tools=[])
    response["choices"][0] = {"finish_reason": "stop", "message": {"content": "Done", "tool_calls": None}}
    assert client.chat([], model="nvidia/test-nemotron", tools=[])["message"] == {"role": "assistant", "content": "Done"}
