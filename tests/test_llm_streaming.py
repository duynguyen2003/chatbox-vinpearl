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
