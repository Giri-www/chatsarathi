"""ChromaDB-backed vector store management for ChatSarathi retrieval."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer

from app.config import logger, settings


@dataclass(slots=True)
class VectorSearchResult:
    """Represents a single vector search hit."""

    document_id: str
    content: str
    metadata: dict[str, Any]
    score: float


class VectorStoreManager:
    """Manage ChromaDB collection lifecycle and vector similarity search."""

    def __init__(self, collection_name: str = "ChatSarathi_documents") -> None:
        """Initialize the vector store manager.

        Args:
            collection_name: Name of the ChromaDB collection to use.
        """
        self.collection_name = collection_name
        self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._collection: Collection | None = None
        self._embedding_model: SentenceTransformer | None = None

    async def get_or_create_collection(self) -> Collection:
        """Get or create the configured ChromaDB collection."""
        if self._collection is None:
            self._collection = await asyncio.to_thread(
                self._client.get_or_create_collection,
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    async def reset_collection(self) -> None:
        """Delete and recreate the active collection."""
        try:
            await asyncio.to_thread(self._client.delete_collection, self.collection_name)
        except Exception:
            logger.info("vectorstore.collection_missing", collection_name=self.collection_name)
        self._collection = None
        await self.get_or_create_collection()

    async def batch_upsert(self, documents: list[dict[str, Any]]) -> None:
        """Upsert a batch of documents with embeddings.

        Args:
            documents: List of document dictionaries containing `id`, `content`, and `metadata`.
        """
        if not documents:
            return
        collection = await self.get_or_create_collection()
        embedding_model = await self._get_embedding_model()
        ids = [doc["id"] for doc in documents]
        texts = [doc["content"] for doc in documents]
        metadatas = [doc.get("metadata", {}) for doc in documents]
        embeddings = await asyncio.to_thread(embedding_model.encode, texts, convert_to_numpy=True)
        await asyncio.to_thread(
            collection.upsert,
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings.tolist(),
        )
        logger.info("vectorstore.batch_upsert", count=len(documents), collection_name=self.collection_name)

    async def similarity_search(self, query: str, k: int = 4) -> list[VectorSearchResult]:
        """Run similarity search against ChromaDB.

        Args:
            query: User search query.
            k: Number of nearest documents to return.

        Returns:
            Ranked vector search results.
        """
        collection = await self.get_or_create_collection()
        embedding_model = await self._get_embedding_model()
        query_embedding = await asyncio.to_thread(embedding_model.encode, [query], convert_to_numpy=True)
        raw = await asyncio.to_thread(
            collection.query,
            query_embeddings=query_embedding.tolist(),
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        results: list[VectorSearchResult] = []
        ids = raw.get("ids", [[]])[0]
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        for idx, document_id in enumerate(ids):
            distance = float(distances[idx]) if idx < len(distances) else 1.0
            results.append(
                VectorSearchResult(
                    document_id=document_id,
                    content=documents[idx],
                    metadata=metadatas[idx] or {},
                    score=max(0.0, 1.0 - distance),
                )
            )
        return results

    async def get_all_documents(self) -> list[dict[str, Any]]:
        """Fetch all indexed documents for keyword retrieval."""
        collection = await self.get_or_create_collection()
        raw = await asyncio.to_thread(collection.get, include=["documents", "metadatas"])
        ids = raw.get("ids", [])
        documents = raw.get("documents", [])
        metadatas = raw.get("metadatas", [])
        if not ids:
            return []
        return [
            {"id": ids[idx], "content": documents[idx], "metadata": metadatas[idx] or {}}
            for idx in range(len(ids))
        ]

    async def _get_embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = await asyncio.to_thread(
                SentenceTransformer,
                "sentence-transformers/all-MiniLM-L6-v2",
            )
        return self._embedding_model


vectorstore_manager = VectorStoreManager()
