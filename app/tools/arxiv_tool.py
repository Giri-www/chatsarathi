"""Academic paper retrieval tool backed by arXiv."""

from __future__ import annotations

import asyncio
from typing import Any

import arxiv
from langchain_core.tools import tool
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import ExternalServiceError, logger


class ArxivTool:
    """Search arXiv for relevant academic papers."""

    name = "arxiv_search"
    description = "Search academic papers from arXiv and return concise metadata with links."

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    async def search(self, query: str, max_results: int = 3) -> list[dict[str, Any]]:
        """Search arXiv asynchronously.

        Args:
            query: Search text.
            max_results: Maximum number of papers to return.

        Returns:
            Paper metadata dictionaries.
        """
        try:
            search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
            results = await asyncio.to_thread(lambda: list(search.results()))
            payload = [
                {
                    "title": result.title,
                    "summary": result.summary[:500],
                    "published": result.published.isoformat() if result.published else None,
                    "pdf_url": result.pdf_url,
                    "entry_id": result.entry_id,
                    "authors": [author.name for author in result.authors],
                }
                for result in results
            ]
            logger.info("tool.arxiv.success", query=query, count=len(payload))
            return payload
        except Exception as exc:
            logger.warning("tool.arxiv.failure", query=query, error=str(exc))
            raise ExternalServiceError("Failed to query arXiv.", code="arxiv_unavailable", details={"query": query}) from exc

    def as_langchain_tool(self) -> Any:
        """Expose the tool as a LangChain-compatible tool."""

        @tool(self.name, return_direct=False)
        async def _tool(query: str) -> str:
            """Search arXiv for scholarly references."""
            results = await self.search(query)
            if not results:
                return "No arXiv results found."
            return "\n".join(
                f"- {item['title']} ({item['published']}): {item['summary']} [{item['pdf_url']}]"
                for item in results
            )

        return _tool
