"""Hybrid retrieval service implementing the RICE retrieval layer."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from rank_bm25 import BM25Okapi

from app.config import logger, settings
from app.models.vectorstore_manager import vectorstore_manager
from app.tools import ArxivTool, TavilyTool, WikiTool


@dataclass(slots=True)
class RetrievedChunk:
    """Normalized retrieval result with citation metadata."""

    source: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievalBundle:
    """Container for local and external retrieval results."""

    context_text: str
    local_results: list[RetrievedChunk]
    external_results: dict[str, Any]


class RAGService:
    """Perform hybrid retrieval and external knowledge augmentation."""

    def __init__(self) -> None:
        """Initialize retrieval dependencies and external tools."""
        self.arxiv_tool = ArxivTool()
        self.wiki_tool = WikiTool()
        self.tavily_tool = TavilyTool()

    async def retrieve(self, query: str, k: int | None = None) -> RetrievalBundle:
        """Retrieve contextual information for a user query.

        Args:
            query: The user query.
            k: Number of local documents to return.

        Returns:
            Retrieval bundle with fused context and citations.
        """
        top_k = k or settings.retrieval_k
        vector_results, keyword_results, external = await asyncio.gather(
            self._vector_search(query, top_k),
            self._keyword_search(query, top_k),
            self._fetch_external_context(query),
        )
        fused_results = self._reciprocal_rank_fusion(vector_results, keyword_results, top_k)
        context_lines = ["Use the following retrieval context when it is relevant:"]
        for idx, item in enumerate(fused_results, start=1):
            source_label = item.metadata.get("source", item.source)
            context_lines.append(f"[R{idx}] {source_label}: {item.content}")
        if external.get("wiki"):
            context_lines.append(f"[Wiki] {external['wiki'].get('summary', '')}")
        if external.get("arxiv"):
            for idx, paper in enumerate(external["arxiv"], start=1):
                context_lines.append(f"[Arxiv {idx}] {paper['title']}: {paper['summary']}")
        if external.get("tavily"):
            for idx, item in enumerate(external["tavily"], start=1):
                context_lines.append(f"[Web {idx}] {item.get('title')}: {item.get('content')}")
        return RetrievalBundle(context_text="\n".join(context_lines), local_results=fused_results, external_results=external)

    async def _vector_search(self, query: str, k: int) -> list[RetrievedChunk]:
        results = await vectorstore_manager.similarity_search(query, k=k)
        return [
            RetrievedChunk(
                source="vector",
                content=result.content,
                score=result.score,
                metadata={"document_id": result.document_id, **result.metadata},
            )
            for result in results
        ]

    async def _keyword_search(self, query: str, k: int) -> list[RetrievedChunk]:
        docs = await vectorstore_manager.get_all_documents()
        if not docs:
            return []
        tokenized_corpus = [doc["content"].lower().split() for doc in docs]
        bm25 = BM25Okapi(tokenized_corpus)
        scores = bm25.get_scores(query.lower().split())
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:k]
        return [
            RetrievedChunk(
                source="bm25",
                content=docs[index]["content"],
                score=float(score),
                metadata={"document_id": docs[index]["id"], **docs[index].get("metadata", {})},
            )
            for index, score in ranked
            if score > 0
        ]

    async def _fetch_external_context(self, query: str) -> dict[str, Any]:
        results = await asyncio.gather(
            self.arxiv_tool.search(query),
            self.wiki_tool.search(query),
            self.tavily_tool.search(query),
            return_exceptions=True,
        )
        external: dict[str, Any] = {"arxiv": [], "wiki": {}, "tavily": []}
        labels = ["arxiv", "wiki", "tavily"]
        for label, result in zip(labels, results, strict=True):
            if isinstance(result, Exception):
                logger.warning("rag.external_fetch_failed", source=label, error=str(result))
                continue
            external[label] = result
        return external

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[RetrievedChunk],
        keyword_results: list[RetrievedChunk],
        top_k: int,
        rrf_k: int = 60,
    ) -> list[RetrievedChunk]:
        fused_scores: defaultdict[str, float] = defaultdict(float)
        chosen: dict[str, RetrievedChunk] = {}
        for result_list in (vector_results, keyword_results):
            for rank, item in enumerate(result_list, start=1):
                doc_id = str(item.metadata.get("document_id", hash(item.content)))
                fused_scores[doc_id] += 1.0 / (rrf_k + rank)
                chosen[doc_id] = item
        ordered = sorted(fused_scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
        final_results: list[RetrievedChunk] = []
        for doc_id, score in ordered:
            result = chosen[doc_id]
            final_results.append(
                RetrievedChunk(
                    source=result.source,
                    content=result.content,
                    score=round(score, 6),
                    metadata=result.metadata,
                )
            )
        return final_results


rag_service = RAGService()
