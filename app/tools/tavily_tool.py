"""Real-time web search via Tavily."""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.tools import tool
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import ExternalServiceError, logger, settings


class TavilyTool:
    """Run real-time web search using the Tavily API."""

    name = "tavily_search"
    description = "Search the web for recent information and citations."

    def __init__(self) -> None:
        """Initialize the Tavily client when an API key is available."""
        self._client = TavilyClient(api_key=settings.tavily_api_key) if settings.tavily_api_key else None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    async def search(self, query: str, max_results: int = 3) -> list[dict[str, Any]]:
        """Search the web through Tavily.

        Args:
            query: Search text.
            max_results: Maximum number of web results.

        Returns:
            Tavily result items.
        """
        if self._client is None:
            return [{"title": "Tavily disabled", "content": "No TAVILY_API_KEY configured.", "url": None}]
        try:
            response = await asyncio.to_thread(
                self._client.search,
                query=query,
                max_results=max_results,
                include_answer=True,
                search_depth="advanced",
            )
            results = response.get("results", [])
            logger.info("tool.tavily.success", query=query, count=len(results))
            return results
        except Exception as exc:
            logger.warning("tool.tavily.failure", query=query, error=str(exc))
            raise ExternalServiceError("Failed to query Tavily.", code="tavily_unavailable", details={"query": query}) from exc

    def as_langchain_tool(self) -> Any:
        """Expose the tool as a LangChain-compatible tool."""

        @tool(self.name, return_direct=False)
        async def _tool(query: str) -> str:
            """Search recent web results with source URLs."""
            results = await self.search(query)
            return "\n".join(
                f"- {item.get('title', 'Result')}: {item.get('content', '')} ({item.get('url')})" for item in results
            )

        return _tool
