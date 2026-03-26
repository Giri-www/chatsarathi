"""Analytics persistence layer backed by async SQLAlchemy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Integer, JSON, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import logger, settings


class Base(DeclarativeBase):
    """Declarative SQLAlchemy base for analytics models."""


class ConversationAnalytics(Base):
    """Persistent analytics record for each chatbot interaction."""

    __tablename__ = "conversation_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), index=True)
    query: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer)
    tools_used: Mapped[list[str]] = mapped_column(JSON)
    rag_sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    hitl_triggered: Mapped[bool] = mapped_column(default=False)
    model_name: Mapped[str] = mapped_column(String(128))
    model_version: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))


@dataclass(slots=True)
class AnalyticsRecord:
    """Normalized analytics payload for writes."""

    session_id: str
    query: str
    response: str
    latency_ms: int
    tools_used: list[str]
    rag_sources: list[dict[str, Any]]
    hitl_triggered: bool
    model_name: str
    model_version: str


class AnalyticsService:
    """Persist and summarize analytics data for the execution layer."""

    def __init__(self) -> None:
        """Initialize async engine and session factory."""
        self._engine = create_async_engine(settings.sqlite_url, future=True)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)

    async def initialize(self) -> None:
        """Create analytics tables if they do not already exist."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def log_interaction(self, record: AnalyticsRecord) -> None:
        """Persist an interaction analytics row."""
        async with self._session_factory() as session:
            session.add(ConversationAnalytics(**asdict(record)))
            await session.commit()
        logger.info("analytics.logged", session_id=record.session_id, latency_ms=record.latency_ms)

    async def get_summary(self, limit: int = 100) -> dict[str, Any]:
        """Return aggregated analytics and recent activity."""
        async with self._session_factory() as session:
            total_stmt = select(func.count(ConversationAnalytics.id))
            avg_latency_stmt = select(func.avg(ConversationAnalytics.latency_ms))
            recent_stmt = select(ConversationAnalytics).order_by(ConversationAnalytics.created_at.desc()).limit(limit)
            total = await session.scalar(total_stmt)
            avg_latency = await session.scalar(avg_latency_stmt)
            recent_rows = (await session.scalars(recent_stmt)).all()
        return {
            "total_requests": int(total or 0),
            "average_latency_ms": round(float(avg_latency or 0.0), 2),
            "recent": [
                {
                    "session_id": row.session_id,
                    "query": row.query,
                    "latency_ms": row.latency_ms,
                    "tools_used": row.tools_used,
                    "hitl_triggered": row.hitl_triggered,
                    "model_name": row.model_name,
                    "model_version": row.model_version,
                    "created_at": row.created_at.isoformat(),
                }
                for row in recent_rows
            ],
        }


analytics_service = AnalyticsService()
