import json

import pytest

from src.backend.api import routes
from src.backend.services.chat_stream import emit_chat_delta, emit_chat_status


def _events(response) -> list[dict]:
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


@pytest.mark.asyncio
async def test_chat_stream_validates_request_before_streaming(client) -> None:
    response = await client.post("/api/v1/chat/stream", json={"message": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_stream_rejects_foreign_session_before_streaming(
    client,
    monkeypatch,
) -> None:
    def deny_session(*_args, **_kwargs):
        raise PermissionError("foreign session")

    monkeypatch.setattr(routes.MemoryService, "ensure_session", deny_session)
    response = await client.post(
        "/api/v1/chat/stream",
        json={"message": "Xin chào", "session_id": "SES-foreign"},
    )

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
async def test_chat_stream_emits_ordered_ndjson_events(client, monkeypatch) -> None:
    monkeypatch.setattr(
        routes.MemoryService,
        "ensure_session",
        lambda *_args, **_kwargs: None,
    )

    def fake_invoke(payload):
        emit_chat_status("generating")
        emit_chat_delta("Xin ")
        emit_chat_delta("chào")
        return {
            **payload,
            "answer": "Xin chào",
            "original_language": "vi",
            "route": "greeting",
            "retrieved_documents": [],
        }

    monkeypatch.setattr(routes.agent_graph, "invoke", fake_invoke)

    response = await client.post(
        "/api/v1/chat/stream",
        json={"message": "Xin chào", "session_id": "SES-stream-test"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"

    events = _events(response)
    assert [event["type"] for event in events] == [
        "start",
        "status",
        "status",
        "delta",
        "delta",
        "final",
    ]
    assert events[0]["session_id"] == "SES-stream-test"
    assert events[1]["stage"] == "analyzing"
    assert "debug" not in events[-1]
    assert events[-1]["answer"] == "Xin chào"
    assert events[-1]["sources"] == []


@pytest.mark.asyncio
async def test_chat_stream_returns_safe_terminal_error(client, monkeypatch) -> None:
    monkeypatch.setattr(
        routes.MemoryService,
        "ensure_session",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        routes.agent_graph,
        "invoke",
        lambda _payload: (_ for _ in ()).throw(RuntimeError("secret provider detail")),
    )

    response = await client.post(
        "/api/v1/chat/stream",
        json={"message": "Xin chào", "session_id": "SES-stream-error"},
    )

    assert response.status_code == 200
    events = _events(response)
    assert [event["type"] for event in events] == ["start", "status", "error"]
    assert events[-1] == {
        "type": "error",
        "code": "CHAT_STREAM_FAILED",
        "message": "Không thể tạo câu trả lời lúc này.",
        "retryable": True,
    }
    assert "secret provider detail" not in response.text
