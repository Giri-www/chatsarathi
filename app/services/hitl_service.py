"""Human-in-the-loop escalation service."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4
from dataclasses import asdict
from app.config import logger, settings


@dataclass(slots=True)
class HITLItem:
    """Represents a human review queue item."""

    id: str
    session_id: str
    query: str
    response: str
    confidence: float
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


class HITLService:
    """Manage confidence-based human escalation and review queue state."""

    def __init__(self) -> None:
        """Initialize in-memory queue storage."""
        self._queue: dict[str, HITLItem] = {}
        self._lock = asyncio.Lock()

    async def maybe_escalate(
        self,
        *,
        session_id: str,
        query: str,
        response: str,
        confidence: float,
        metadata: dict[str, Any] | None = None,
    ) -> HITLItem | None:
        """Escalate to human review when confidence is below threshold."""
        if confidence > settings.hitl_confidence_threshold:
            return None
        return await self.escalate(
            session_id=session_id,
            query=query,
            response=response,
            confidence=confidence,
            metadata=metadata,
        )

    async def escalate(
        self,
        *,
        session_id: str,
        query: str,
        response: str,
        confidence: float,
        metadata: dict[str, Any] | None = None,
    ) -> HITLItem:
        """Create a new queue item for human review."""
        async with self._lock:
            item = HITLItem(
                id=str(uuid4()),
                session_id=session_id,
                query=query,
                response=response,
                confidence=confidence,
                metadata=metadata or {},
            )
            self._queue[item.id] = item
            logger.info("hitl.escalated", item_id=item.id, session_id=session_id, confidence=confidence)
            return item

    async def update_status(self, item_id: str, status: str) -> HITLItem | None:
        """Update review item status."""
        async with self._lock:
            item = self._queue.get(item_id)
            if item is None:
                return None
            item.status = status
            logger.info("hitl.status_updated", item_id=item_id, status=status)
            return item
   
    async def list_queue(self) -> list[dict[str, Any]]:
        """Return queue contents ordered by creation time descending."""
        items = sorted(self._queue.values(), key=lambda item: item.created_at, reverse=True)
        return [asdict(item) for item in items]


hitl_service = HITLService()
