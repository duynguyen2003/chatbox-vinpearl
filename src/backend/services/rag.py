from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

from src.backend.config import get_settings


class RAGService:
    def __init__(self) -> None:
        settings = get_settings()
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)

        self.settings = settings
        self.model = SentenceTransformer(
            settings.local_embedding_model,
            device=settings.embedding_device,
        )

        self.chroma = chromadb.PersistentClient(path=str(settings.chroma_dir))
        self.collection = self.chroma.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        passages = [f"passage: {text}" for text in texts]
        embeddings = self.model.encode(
            passages,
            batch_size=self.settings.embedding_batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        embedding = self.model.encode(
            f"query: {query}",
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embedding.tolist()

    # Backward-compatible alias for old ingestion code.
    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        if self.collection.count() == 0:
            raise RuntimeError(
                "Vector database is empty. Run: python -m src.backend.services.ingest_postgres --reset"
            )

        query_embedding = self.embed_query(query)
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k or self.settings.top_k,
            include=["documents", "metadatas", "distances"],
        )

        output: list[dict[str, Any]] = []
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for text, metadata, distance in zip(documents, metadatas, distances):
            score = max(0.0, 1.0 - float(distance))
            output.append(
                {
                    "text": text,
                    "metadata": metadata or {},
                    "score": round(score, 4),
                }
            )
        return output

    def build_context(self, documents: list[dict[str, Any]]) -> str:
        blocks: list[str] = []
        total = 0

        for index, item in enumerate(documents, start=1):
            metadata = item["metadata"]
            block = (
                f"[SOURCE {index}]\n"
                f"type: {metadata.get('entity_type') or metadata.get('category')}\n"
                f"name: {metadata.get('entity_name') or metadata.get('source_file')}\n"
                f"destination: {metadata.get('destination')}\n"
                f"url: {metadata.get('source_url')}\n"
                f"relevance_score: {item.get('score')}\n"
                f"content:\n{item['text']}\n"
            )
            if total + len(block) > self.settings.max_context_chars:
                break
            blocks.append(block)
            total += len(block)

        return "\n---\n".join(blocks)
