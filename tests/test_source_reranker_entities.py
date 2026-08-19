from src.backend.services.source_reranker import SourceReranker


def test_extract_entities_from_nested_json_shapes() -> None:
    answer = """{
      "sections": [
        {"title": "Vinpearl Resort Nha Trang"},
        {"items": [{"venue_name": "Almaz Convention Center"}]}
      ],
      "context": {"text": "Hon Tre Island"}
    }"""

    assert SourceReranker._extract_answer_entities(answer) == [
        "Vinpearl Resort Nha Trang",
        "Almaz Convention Center",
        "Hon Tre Island",
    ]


def test_extract_entities_from_json_embedded_in_prose_and_fence() -> None:
    answer = """Recommended result:
```json
{"topics": [{"title": "VinWonders Phu Quoc", "stops": [{"name": "Grand World"}]}]}
```
Use the official links below.
"""

    assert SourceReranker._extract_answer_entities(answer) == [
        "VinWonders Phu Quoc",
        "Grand World",
    ]


def test_extract_entities_from_truncated_json_fields() -> None:
    answer = (
        '{"topics": [{"title": "Vinpearl Golf Nha Trang", '
        '"stops": [{"name": "Hon Tre Island"}'
    )

    assert set(SourceReranker._extract_answer_entities(answer)) == {
        "Vinpearl Golf Nha Trang",
        "Hon Tre Island",
    }
