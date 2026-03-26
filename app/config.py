"""Configuration, logging, and shared application primitives for ChatSarathi."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class ChatSarathiError(Exception):
    """Base application exception for ChatSarathi."""

    def __init__(self, message: str, *, code: str = "ChatSarathi_error", details: dict[str, Any] | None = None) -> None:
        """Initialize the application exception.

        Args:
            message: Human-readable error description.
            code: Stable machine-friendly error code.
            details: Optional structured details for logs and responses.
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ExternalServiceError(ChatSarathiError):
    """Raised when an external dependency cannot be reached or parsed."""


class RetrievalError(ChatSarathiError):
    """Raised when retrieval or indexing fails."""


class ErrorResponse(BaseModel):
    """Standard structured error response payload."""

    error: str
    code: str
    details: dict[str, Any] = Field(default_factory=dict)


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    app_name: str = "ChatSarathi"
    api_prefix: str = "/api"
    
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "ollama"))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3"))
    anthropic_api_key: str | None = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_model_version: str = "20250514"
    tavily_api_key: str | None = field(default_factory=lambda: os.getenv("TAVILY_API_KEY"))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))
    chroma_persist_dir: str = field(default_factory=lambda: os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"))
    sqlite_url: str = field(default_factory=lambda: os.getenv("SQLITE_URL", "sqlite+aiosqlite:///./ChatSarathi_analytics.db"))
    hitl_confidence_threshold: float = field(
        default_factory=lambda: float(os.getenv("HITL_CONFIDENCE_THRESHOLD", "0.4"))
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    retrieval_k: int = field(default_factory=lambda: int(os.getenv("RETRIEVAL_K", "4")))
    memory_window: int = field(default_factory=lambda: int(os.getenv("MEMORY_WINDOW", "10")))
    request_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT_SECONDS", "45")))

    def ensure_directories(self) -> None:
        """Create local storage directories required by the app."""
        Path(self.chroma_persist_dir).mkdir(parents=True, exist_ok=True)


def configure_logging(level: str) -> None:
    """Configure structured JSON logging for the application.

    Args:
        level: Logging severity threshold.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level.upper()),
        cache_logger_on_first_use=True,
    )


settings = Settings()
settings.ensure_directories()
configure_logging(settings.log_level)
logger = structlog.get_logger("ChatSarathi")
