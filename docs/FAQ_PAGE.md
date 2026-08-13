# FAQ Page

## Summary

This feature adds a searchable FAQ page backed by the PostgreSQL FAQ table.
The frontend page is available at `/faq`, and it reads data from
`GET /api/v1/faqs`.

The implementation is intentionally separated from the AI chat flow. Chat
history, RAG retrieval, and structured AI responses are not changed by this
feature.

## User-Facing Changes

- Adds a dedicated FAQ page at `/faq`.
- Adds a footer link that points to `/faq`.
- Shows an accordion list of questions and answers.
- Supports search by keyword.
- Supports category filtering.
- Supports pagination through URL query params.
- Keeps search/category/page state in the URL so links are shareable.
- Shows loading, empty, and error states.

## Frontend Files

- `src/Frontend/pages/Faq.jsx`
  - Page shell, hero, search input, category filter, pagination, and API loading.
- `src/Frontend/components/FaqList.jsx`
  - Accessible accordion list for FAQ items.
- `src/Frontend/styles/pages/Faq.css`
  - FAQ page layout and responsive styles.
- `src/Frontend/services/api.js`
  - Adds `fetchFaqs(filters)`.
- `src/Frontend/routes/AppRoutes.jsx`
  - Registers the `/faq` route.
- `src/Frontend/components/Footer.jsx`
  - Updates the FAQ footer link to navigate to `/faq`.
- `src/Frontend/types.js`
  - Adds JSDoc typedefs for FAQ API payloads.
- `src/Frontend/image/faq.jpg.webp`
  - Hero background image used by the FAQ page.

## Backend Files

- `src/backend/api/faq_routes.py`
  - Exposes `GET /api/v1/faqs`.
- `src/backend/models/faq.py`
  - Pydantic response models.
- `src/backend/repositories/faq_repository.py`
  - Reads FAQ data with search, category filter, pagination, and category counts.
- `src/backend/main.py`
  - Includes the FAQ router.

## API Contract

Endpoint:

```http
GET /api/v1/faqs?q=booking&category=Policy&page=1&page_size=20&lang=en
```

Query params:

- `q`: optional keyword search across question and answer.
- `category`: optional exact category filter.
- `destination`: optional destination id filter.
- `page`: 1-indexed page number.
- `page_size`: page size, capped by the backend.
- `lang`: requested frontend language.

Response shape:

```json
{
  "items": [
    {
      "id": "faq-id",
      "category": "Booking",
      "subcategory": null,
      "question": "Question text",
      "answer": "Answer text",
      "destination_id": null,
      "content_language": "en",
      "sort_order": 1
    }
  ],
  "categories": [
    {"name": "Booking", "count": 12}
  ],
  "page": 1,
  "page_size": 20,
  "total": 42,
  "content_language": "en",
  "requested_language": "en",
  "translation_fallback": false
}
```

## Notes For Reviewers

- Category counts are calculated from the current search and destination filter,
  but not from the selected category. This lets the sidebar show useful counts
  while one category is active.
- The repository removes duplicate questions before paginating.
- Current FAQ content is treated as English-first. If the requested language is
  different, the API marks `translation_fallback=true`.
- The page includes fallback UI labels, so missing translation keys do not break
  rendering.

## Verification

Recommended checks before merging:

```bash
npm.cmd run build
npm.cmd run lint
pytest tests/test_faq_api.py
```

Manual smoke test:

1. Open `/faq`.
2. Search for a common keyword such as `booking`.
3. Toggle a category filter.
4. Move between pages if multiple pages are available.
5. Expand/collapse FAQ answers.
