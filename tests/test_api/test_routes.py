"""Kiểm thử API.

``test_agent_status`` cũ gọi ``GET /api/v1/status`` — endpoint mã mẫu của
template, chưa từng tồn tại trong src/api/routes.py. Thay bằng các phép kiểm
validate đầu vào của /api/v1/chat: chúng chạy trước khi handler gọi LLM nên
không cần API key hay Chroma.
"""

import pytest

from src.backend.api import routes


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_empty_message(client):
    response = await client.post("/api/v1/chat", json={"message": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_missing_message(client):
    response = await client.post("/api/v1/chat", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_message_too_long(client):
    """ChatRequest giới hạn 10.000 ký tự."""
    response = await client.post("/api/v1/chat", json={"message": "x" * 10_001})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unknown_route_returns_404(client):
    response = await client.get("/api/v1/khong-ton-tai")
    assert response.status_code == 404


def test_policy_sources_exclude_unrelated_entities(monkeypatch) -> None:
    class StubReranker:
        def rerank(self, **_kwargs):
            return [
                {
                    "metadata": {"entity_name": "Vinpearl", "entity_type": "brand"},
                },
                {
                    "best_source_url": "https://vinpearl.com/vi/general-terms",
                    "metadata": {
                        "entity_name": "General regulations",
                        "entity_type": "policy_document",
                    },
                },
                {
                    "best_source_url": "https://booking.vinpearl.com/promotion",
                    "metadata": {
                        "entity_name": "Unrelated promotion",
                        "entity_type": "promotion",
                    },
                },
            ]

    monkeypatch.setattr(routes, "get_source_reranker", lambda: StubReranker())

    sources = routes._build_sources(
        {
            "answer": '{"topics": [{"title": "Quy định trẻ em"}]}',
            "detected_intents": ["policy"],
            "retrieved_documents": [{"metadata": {"entity_type": "policy_document"}}],
        }
    )

    assert [source.source_file for source in sources] == ["General regulations"]
    assert sources[0].path == "https://vinpearl.com/vi/general-terms"


def test_mixed_intents_keep_non_policy_sources(monkeypatch) -> None:
    class StubReranker:
        def rerank(self, **kwargs):
            assert kwargs["max_sources"] == 5
            return [
                {
                    "best_source_url": "https://vinpearl.com/en/hotels/vinpearl-resort-nha-trang",
                    "metadata": {
                        "entity_name": "Vinpearl Resort Nha Trang",
                        "entity_type": "hotel",
                        "destination_id": "nha-trang",
                    },
                },
                {
                    "best_source_url": "https://vinpearl.com/vi/terms-of-use",
                    "metadata": {
                        "entity_name": "General Terms",
                        "entity_type": "policy_document",
                        "destination_id": "nha-trang",
                    },
                },
            ]

    monkeypatch.setattr(routes, "get_source_reranker", lambda: StubReranker())

    sources = routes._build_sources(
        {
            "answer": "Vinpearl Resort Nha Trang",
            "detected_destination_ids": ["nha-trang"],
            "detected_intents": ["hotel", "policy"],
            "retrieved_documents": [{"metadata": {"entity_type": "hotel"}}],
        }
    )

    assert [source.source_file for source in sources] == [
        "Vinpearl Resort Nha Trang",
        "General Terms",
    ]
