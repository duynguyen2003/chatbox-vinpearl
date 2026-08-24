"""Tests cho FAQ API endpoints và repository."""

from fastapi.testclient import TestClient

from src.backend.main import app

client = TestClient(app)


def test_get_faqs_basic():
    """Test endpoint GET /api/v1/faqs trả 200 và structure đúng."""
    response = client.get("/api/v1/faqs")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "categories" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["categories"], list)
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_get_faqs_pagination():
    """Test pagination params."""
    response = client.get("/api/v1/faqs?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["items"]) <= 5


def test_get_faqs_search():
    """Test search parameter."""
    response = client.get("/api/v1/faqs?q=booking")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["items"], list)


def test_get_faqs_category_filter():
    """Test category filter."""
    # First get categories
    res1 = client.get("/api/v1/faqs")
    categories = res1.json().get("categories", [])

    if categories:
        cat_name = categories[0]["name"]
        res2 = client.get(f"/api/v1/faqs?category={cat_name}")
        assert res2.status_code == 200
        data2 = res2.json()
        for item in data2["items"]:
            assert item["category"] == cat_name
