"""FastAPI routes for chat, WebSocket streaming, HITL, and analytics."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.config import ErrorResponse, ChatSarathiError, logger
from app.memory.memory_manager import memory_manager
from app.services.analytics_service import AnalyticsRecord, analytics_service
from app.services.hitl_service import hitl_service
from app.services.llm_service import LLMResponse, llm_service

router = APIRouter()


class ChatRequest(BaseModel):
    """REST chat request schema."""

    session_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)


class SourceCitation(BaseModel):
    """Source citation payload returned with answers."""

    label: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """REST chat response schema."""

    session_id: str
    response: str
    confidence: float
    model_name: str
    model_version: str
    tools_used: list[str] = Field(default_factory=list)
    rag_sources: list[SourceCitation] = Field(default_factory=list)
    hitl_triggered: bool = False
    hitl_item_id: str | None = None


class EscalationRequest(BaseModel):
    """Manual escalation request schema."""

    session_id: str
    query: str
    response: str
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EscalationResponse(BaseModel):
    """Escalation response schema."""

    item_id: str
    status: str


@router.post("/chat", response_model=ChatResponse, responses={500: {"model": ErrorResponse}})
async def chat(request: ChatRequest) -> ChatResponse:
    """Synchronous fallback chat endpoint."""
    started_at = time.perf_counter()
    try:
        result = await llm_service.generate(request.session_id, request.query)
        hitl_item = await hitl_service.maybe_escalate(
            session_id=request.session_id,
            query=request.query,
            response=result.response_text,
            confidence=result.hitl_confidence,
            metadata={"tools_used": result.tools_used},
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        await analytics_service.log_interaction(
            AnalyticsRecord(
                session_id=request.session_id,
                query=request.query,
                response=result.response_text,
                latency_ms=latency_ms,
                tools_used=result.tools_used,
                rag_sources=result.rag_sources,
                hitl_triggered=hitl_item is not None,
                model_name=result.model_name,
                model_version=result.model_version,
            )
        )
        return ChatResponse(
            session_id=request.session_id,
            response=result.response_text,
            confidence=result.hitl_confidence,
            model_name=result.model_name,
            model_version=result.model_version,
            tools_used=result.tools_used,
            rag_sources=[SourceCitation(**source) for source in result.rag_sources],
            hitl_triggered=hitl_item is not None,
            hitl_item_id=hitl_item.id if hitl_item else None,
        )
    except ChatSarathiError as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(error=exc.message, code=exc.code, details=exc.details).model_dump(),
        ) from exc


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for real-time token streaming."""
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            query = payload.get("query")
            if not query:
                await websocket.send_json({"type": "error", "message": "Missing query."})
                continue
            started_at = time.perf_counter()
            final_payload: LLMResponse | None = None
            try:
                async for event in llm_service.generate_stream(session_id, query):
                    if event["type"] == "token":
                        await websocket.send_json(event)
                    elif event["type"] == "complete":
                        final_payload = event["payload"]
            except ChatSarathiError as exc:
                logger.warning(
                    "websocket.chat_error",
                    session_id=session_id,
                    code=exc.code,
                    details=exc.details,
                )
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": exc.message,
                        "code": exc.code,
                        "details": exc.details,
                    }
                )
                continue
            except Exception as exc:
                logger.exception("websocket.unexpected_error", session_id=session_id, error=str(exc))
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Unexpected error while processing the chat request.",
                        "code": "websocket_chat_failed",
                    }
                )
                continue

            if final_payload is None:
                await websocket.send_json({"type": "error", "message": "No response generated."})
                continue
            hitl_item = await hitl_service.maybe_escalate(
                session_id=session_id,
                query=query,
                response=final_payload.response_text,
                confidence=final_payload.hitl_confidence,
                metadata={"tools_used": final_payload.tools_used},
            )
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            await analytics_service.log_interaction(
                AnalyticsRecord(
                    session_id=session_id,
                    query=query,
                    response=final_payload.response_text,
                    latency_ms=latency_ms,
                    tools_used=final_payload.tools_used,
                    rag_sources=final_payload.rag_sources,
                    hitl_triggered=hitl_item is not None,
                    model_name=final_payload.model_name,
                    model_version=final_payload.model_version,
                )
            )
            await websocket.send_json(
                {
                    "type": "complete",
                    "response": final_payload.response_text,
                    "confidence": final_payload.hitl_confidence,
                    "model_name": final_payload.model_name,
                    "model_version": final_payload.model_version,
                    "tools_used": final_payload.tools_used,
                    "rag_sources": final_payload.rag_sources,
                    "hitl_triggered": hitl_item is not None,
                    "hitl_item_id": hitl_item.id if hitl_item else None,
                }
            )
    except WebSocketDisconnect:
        logger.info("websocket.disconnected", session_id=session_id)


@router.post("/hitl/escalate", response_model=EscalationResponse)
async def escalate(request: EscalationRequest) -> EscalationResponse:
    """Manually flag a message for human review."""
    item = await hitl_service.escalate(
        session_id=request.session_id,
        query=request.query,
        response=request.response,
        confidence=request.confidence,
        metadata=request.metadata,
    )
    return EscalationResponse(item_id=item.id, status=item.status)


@router.get("/hitl/queue")
async def get_hitl_queue() -> dict[str, Any]:
    """Return the current HITL review queue."""
    return {"items": await hitl_service.list_queue()}


@router.get("/analytics/summary")
async def analytics_summary() -> dict[str, Any]:
    """Return analytics summary data for dashboards."""
    return await analytics_service.get_summary()


@router.get("/sessions")
async def list_sessions() -> dict[str, Any]:
    """List known conversation sessions."""
    return {"sessions": await memory_manager.list_sessions()}


@router.get("/sessions/{session_id}/history")
async def session_history(session_id: str) -> dict[str, Any]:
    """Fetch recent history for a session."""
    return {"session_id": session_id, "history": await memory_manager.get_recent_history(session_id)}
