import pytest

from app.web_mvp import llm


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response, calls):
        self.response = response
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if callable(self.response):
            return self.response(url, kwargs)
        return self.response


def configure(monkeypatch, provider="gemini", gemini_key="g-key", openai_key="o-key"):
    monkeypatch.setattr(llm.config, "LLM_PROVIDER", provider)
    monkeypatch.setattr(llm.config, "GEMINI_API_KEY", gemini_key)
    monkeypatch.setattr(llm.config, "GEMINI_MODEL", "gemini-test")
    monkeypatch.setattr(llm.config, "OPENAI_API_KEY", openai_key)
    monkeypatch.setattr(llm.config, "OPENAI_MODEL", "openai-test")
    monkeypatch.setattr(llm.config, "LEGACY_LLM_API_KEY", "")


@pytest.mark.asyncio
async def test_gemini_provider_uses_server_side_header_and_json_mode(monkeypatch):
    calls = []
    configure(monkeypatch, provider="gemini")
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kwargs: FakeClient(
        FakeResponse({"candidates": [{"content": {"parts": [{"text": '{"intent":"GENERAL_QUERY"}'}]}}]}), calls
    ))

    result = await llm.complete("system", "hello", json_mode=True)

    assert result == '{"intent":"GENERAL_QUERY"}'
    url, kwargs = calls[0]
    assert "models/gemini-test:generateContent" in url
    assert kwargs["headers"]["x-goog-api-key"] == "g-key"
    assert kwargs["json"]["generationConfig"]["responseMimeType"] == "application/json"


@pytest.mark.asyncio
async def test_openai_provider_uses_bearer_key_and_selected_model(monkeypatch):
    calls = []
    configure(monkeypatch, provider="openai")
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kwargs: FakeClient(
        FakeResponse({"choices": [{"message": {"content": "grounded answer"}}]}), calls
    ))

    result = await llm.complete("system", "question")

    assert result == "grounded answer"
    url, kwargs = calls[0]
    assert url == "https://api.openai.com/v1/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer o-key"
    assert kwargs["json"]["model"] == "openai-test"


@pytest.mark.asyncio
async def test_missing_preferred_key_uses_available_hosted_provider(monkeypatch):
    calls = []
    configure(monkeypatch, provider="gemini", gemini_key="", openai_key="fallback-key")
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kwargs: FakeClient(
        FakeResponse({"choices": [{"message": {"content": "fallback"}}]}), calls
    ))

    assert llm.configured_provider() == "openai"
    assert await llm.complete("system", "question") == "fallback"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_no_keys_or_provider_failures_return_none(monkeypatch):
    calls = []
    configure(monkeypatch, provider="gemini", gemini_key="", openai_key="")
    assert await llm.complete("system", "question") is None

    configure(monkeypatch, provider="gemini")
    def fail(url, kwargs):
        raise RuntimeError("provider unavailable")
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kwargs: FakeClient(fail, calls))
    assert await llm.complete("system", "question") is None