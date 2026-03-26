"""LangServe integration for ChatSarathi."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.llm_service import llm_service

try:
    from langchain_core.runnables import RunnableLambda
except ImportError:  # pragma: no cover - optional dependency at runtime
    RunnableLambda = None


class ChatSarathiLangServeInput(BaseModel):
    """Input schema exposed through LangServe."""

    session_id: str = Field(default="default-session", min_length=1)
    query: str = Field(..., min_length=1)


class ChatSarathiLangServeOutput(BaseModel):
    """Output schema exposed through LangServe."""

    session_id: str
    response: str
    confidence: float
    model_name: str
    model_version: str
    tools_used: list[str] = Field(default_factory=list)
    rag_sources: list[dict] = Field(default_factory=list)


async def _invoke_chat(payload: ChatSarathiLangServeInput) -> ChatSarathiLangServeOutput:
    """Invoke the existing ChatSarathi LLM service."""
    result = await llm_service.generate(payload.session_id, payload.query)
    return ChatSarathiLangServeOutput(
        session_id=result.session_id,
        response=result.response_text,
        confidence=result.hitl_confidence,
        model_name=result.model_name,
        model_version=result.model_version,
        tools_used=result.tools_used,
        rag_sources=result.rag_sources,
    )


def get_langserve_runnable():
    """Return a LangChain runnable when LangServe dependencies are installed."""
    if RunnableLambda is None:
        return None
    return RunnableLambda(_invoke_chat).with_types(
        input_type=ChatSarathiLangServeInput,
        output_type=ChatSarathiLangServeOutput,
    )
