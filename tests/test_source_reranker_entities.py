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


def test_exact_entity_prefers_canonical_property_over_broad_highlight() -> None:
    reranker = object.__new__(SourceReranker)
    reranker._load_cache = lambda: [
        {
            "id": "highlight",
            "text": (
                "Vinpearl Beachfront Nha Trang, Vinpearl Resort Nha Trang, "
                "Vinpearl Luxury Nha Trang"
            ),
            "metadata": {
                "entity_name": "Vinpearl Beachfront Nha Trang",
                "entity_type": "org_highlight",
                "source_url": "https://vinpearl.com/en/about-us",
            },
            "searchable": (
                "vinpearl beachfront nha trang vinpearl resort nha trang "
                "vinpearl luxury nha trang"
            ),
        },
        {
            "id": "property",
            "text": "Vinpearl Beachfront Nha Trang",
            "metadata": {
                "entity_name": "Vinpearl Beachfront Nha Trang",
                "entity_type": "property",
                "source_url": (
                    "https://vinpearl.com/en/hotels/"
                    "vinpearl-beachfront-nha-trang"
                ),
            },
            "searchable": "vinpearl beachfront nha trang",
        },
    ]

    selected = reranker.rerank(
        answer=(
            "**Vinpearl Beachfront Nha Trang**\n"
            "**Vinpearl Resort Nha Trang**\n"
            "**Vinpearl Luxury Nha Trang**"
        ),
        retrieved_documents=[],
        max_sources=1,
    )

    assert selected[0]["metadata"]["entity_type"] == "property"
    assert selected[0]["best_source_url"].endswith(
        "/hotels/vinpearl-beachfront-nha-trang"
    )
