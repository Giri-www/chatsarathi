"""Wikipedia summary retrieval tool."""

from __future__ import annotations

import asyncio
from typing import Any

import wikipedia
from langchain_core.tools import tool
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import ExternalServiceError, logger


class WikiTool:
    """Fetch Wikipedia summaries for user questions."""

    name = "wikipedia_summary"
    description = "Look up Wikipedia summaries for general knowledge topics."

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    async def search(self, query: str) -> dict[str, Any]:
        """Search and summarize Wikipedia content.

        Args:
            query: User topic or phrase.

        Returns:
            Summary dictionary with title and source URL.
        """
        try:
            page_title = await asyncio.to_thread(wikipedia.search, query, 1)
            if not page_title:
                return {"title": query, "summary": "No Wikipedia result found.", "url": None}
            page = await asyncio.to_thread(wikipedia.page, page_title[0], auto_suggest=False)
            summary = await asyncio.to_thread(wikipedia.summary, page_title[0], sentences=4, auto_suggest=False)
            payload = {"title": page.title, "summary": summary, "url": page.url}
            logger.info("tool.wikipedia.success", query=query, title=page.title)
            return payload
        except Exception as exc:
            logger.warning("tool.wikipedia.failure", query=query, error=str(exc))
            raise ExternalServiceError(
                "Failed to query Wikipedia.", code="wikipedia_unavailable", details={"query": query}
            ) from exc

    def as_langchain_tool(self) -> Any:
        """Expose the tool as a LangChain-compatible tool."""

        @tool(self.name, return_direct=False)
        async def _tool(query: str) -> str:
            """Fetch a concise Wikipedia summary."""
            result = await self.search(query)
            return f"{result['title']}: {result['summary']} ({result['url']})"

        return _tool
