from fastapi.testclient import TestClient

from src.backend.main import app

client = TestClient(app)


def test_attractions_support_filters_and_pagination() -> None:
    response = client.get("/api/v1/discovery/attractions?page=1&page_size=3&lang=vi")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= len(payload["items"]) == 3
    assert payload["destinations"]
    assert "experience" in payload["kinds"]
    assert all(item["image_url"] for item in payload["items"])

    destination_id = payload["items"][0]["destination_id"]
    filtered = client.get(
        "/api/v1/discovery/attractions",
        params={"destination": destination_id, "kind": "experience"},
    )
    assert filtered.status_code == 200
    assert all(
        item["destination_id"] == destination_id and item["kind"] == "experience"
        for item in filtered.json()["items"]
    )


def test_attraction_detail_and_missing_item() -> None:
    listing = client.get("/api/v1/discovery/attractions?page_size=1").json()
    attraction_id = listing["items"][0]["id"]
    response = client.get(f"/api/v1/discovery/attractions/{attraction_id}")
    assert response.status_code == 200
    assert response.json()["id"] == attraction_id
    assert response.json()["destination_name"]
    assert response.json()["source_url"].startswith("https://")
    assert client.get("/api/v1/discovery/attractions/not-found").status_code == 404


def test_golf_list_and_detail_include_features() -> None:
    response = client.get("/api/v1/discovery/golf?page_size=20")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 6
    assert len(payload["items"]) == 6
    course = next(item for item in payload["items"] if item["feature_count"] > 0)

    detail = client.get(f"/api/v1/discovery/golf/{course['id']}")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["features"]
    assert detail_payload["feature_count"] == len(detail_payload["features"])
    assert any(item["image_url"] for item in detail_payload["features"])


def test_golf_missing_item_returns_404() -> None:
    assert client.get("/api/v1/discovery/golf/not-found").status_code == 404


def test_mice_list_filters_by_layout_and_capacity() -> None:
    response = client.get("/api/v1/discovery/mice?page_size=20")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 10
    assert len(payload["items"]) == 10
    assert any(item["room_count"] > 0 for item in payload["items"])

    filtered = client.get(
        "/api/v1/discovery/mice",
        params={"layout": "theater", "min_capacity": 500, "page_size": 20},
    )
    assert filtered.status_code == 200
    filtered_items = filtered.json()["items"]
    assert filtered_items
    assert all((item["max_capacity"] or 0) >= 500 for item in filtered_items)


def test_mice_detail_includes_rooms_and_capacities() -> None:
    listing = client.get("/api/v1/discovery/mice?page_size=20").json()
    venue = next(item for item in listing["items"] if item["room_count"] > 0)
    response = client.get(f"/api/v1/discovery/mice/{venue['id']}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["rooms"]
    assert any(room["capacities"] for room in payload["rooms"])
    assert client.get("/api/v1/discovery/mice/not-found").status_code == 404


def test_discovery_rejects_invalid_filters() -> None:
    assert (
        client.get("/api/v1/discovery/attractions?kind=invalid").status_code == 422
    )
    assert client.get("/api/v1/discovery/mice?layout=invalid").status_code == 422
    assert client.get("/api/v1/discovery/mice?min_capacity=0").status_code == 422
