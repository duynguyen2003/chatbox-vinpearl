from types import SimpleNamespace

from src.backend.services import llm as llm_module


def _service():
    service = llm_module.LLMService.__new__(llm_module.LLMService)
    service.model = "test-model"
    service.api_key = "test-key"
    service.api_key_backup = None
    service.base_url = None
    service.temperature = 0.2
    service.max_tokens = 100
    service.timeout = 10
    service.max_retries = 1
    return service


def test_stream_text_requests_provider_stream_and_preserves_spacing(monkeypatch) -> None:
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return iter(
            [
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="Xin "))]
                ),
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="chào"))]
                ),
            ]
        )

    monkeypatch.setattr(llm_module, "completion", fake_completion)

    chunks = list(
        _service().stream_text(
            system_prompt="system",
            user_prompt="user",
        )
    )

    assert captured["stream"] is True
    assert chunks == ["Xin ", "chào"]
    assert "".join(chunks) == "Xin chào"


def test_text_switches_to_configured_fallback_endpoint(monkeypatch) -> None:
    service = _service()
    service.fallback_model = "fallback-model"
    service.fallback_api_key = "fallback-key"
    service.fallback_base_url = "https://fallback.example/v1"
    calls = []

    class RetryableAuthenticationError(Exception):
        pass

    def fake_completion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RetryableAuthenticationError("primary unavailable")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="fallback ok"))]
        )

    monkeypatch.setattr(
        llm_module,
        "AuthenticationError",
        RetryableAuthenticationError,
    )
    monkeypatch.setattr(llm_module, "completion", fake_completion)

    answer = service.text(system_prompt="system", user_prompt="user")

    assert answer == "fallback ok"
    assert calls[0]["model"] == "test-model"
    assert calls[0]["api_key"] == "test-key"
    assert "api_base" not in calls[0]
    assert calls[1]["model"] == "fallback-model"
    assert calls[1]["api_key"] == "fallback-key"
    assert calls[1]["api_base"] == "https://fallback.example/v1"
