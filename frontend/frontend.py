"""Streamlit frontend for ChatSarathi."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
from typing import Any
from urllib import request as urllib_request

import altair as alt
import pandas as pd
import streamlit as st
import websockets

BACKEND_HTTP_URL = os.getenv("ChatSarathi_BACKEND_URL", "http://localhost:8000")
BACKEND_WS_URL = os.getenv("ChatSarathi_WS_URL", "ws://localhost:8000/api/ws/chat")


def run_async(coro):
    """Run async coroutine safely inside Streamlit."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


def http_get_json(path: str) -> dict[str, Any]:
    """Fetch JSON from the backend."""
    with urllib_request.urlopen(f"{BACKEND_HTTP_URL}{path}") as response:
        return json.loads(response.read().decode("utf-8"))


def http_post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST a JSON payload to the backend."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        f"{BACKEND_HTTP_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


async def stream_chat(
    session_id: str,
    query: str,
    on_token: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Send a message over WebSocket and collect streamed output."""
    url = f"{BACKEND_WS_URL}/{session_id}"
    collected = ""
    final_payload: dict[str, Any] = {}
    async with websockets.connect(url) as websocket:
        await websocket.send(json.dumps({"query": query}))
        while True:
            raw = await websocket.recv()
            message = json.loads(raw)
            if message["type"] == "token":
                collected += message["content"]
                if on_token is not None:
                    on_token(collected)
            elif message["type"] == "complete":
                final_payload = message
                break
            elif message["type"] == "error":
                raise RuntimeError(message["message"])
    final_payload["response"] = collected.strip() or final_payload.get("response", "")
    return final_payload


def render_sources(sources: list[dict[str, Any]]) -> None:
    """Render response citations as expandable cards."""
    for idx, source in enumerate(sources, start=1):
        with st.expander(f"Source {idx}: {source.get('label', 'citation')}"):
            st.write(source.get("content", ""))
            st.json(source.get("metadata", {}))


st.set_page_config(page_title="ChatSarathi", layout="wide")
st.title("ChatSarathi")
st.caption("Production-grade intelligent chatbot with RAG, tools, analytics, and HITL.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = "default-session"

with st.sidebar:
    st.header("Session")
    st.session_state.session_id = st.text_input("Session ID", value=st.session_state.session_id)

    if st.button("Refresh Sessions"):
        st.session_state.available_sessions = http_get_json("/api/sessions").get("sessions", [])
    for session in st.session_state.get("available_sessions", []):
        st.write(session)

    st.header("Analytics")
    analytics = http_get_json("/api/analytics/summary")
    st.metric("Total Requests", analytics.get("total_requests", 0))
    st.metric("Avg Latency (ms)", analytics.get("average_latency_ms", 0))
    recent = analytics.get("recent", [])

    if recent:
        df = pd.DataFrame(recent)

        chart = alt.Chart(df).mark_bar().encode(
            x="session_id:N",
            y="latency_ms:Q",
            tooltip=["query", "latency_ms", "model_name", "model_version"],
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No analytics data yet")
    queue = http_get_json("/api/hitl/queue").get("items", [])
    for item in queue[:10]:
        with st.expander(f"{item['status']} | {item['session_id']}"):
            st.write(item["query"])
            st.write(item["response"])
            st.write(f"Confidence: {item['confidence']}")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            render_sources(message["sources"])
        if message["role"] == "assistant" and st.button(
            f"Escalate to human review ({message['id']})",
            key=f"escalate_{message['id']}",
        ):
            response = http_post_json(
                "/api/hitl/escalate",
                {
                    "session_id": st.session_state.session_id,
                    "query": message.get("query", ""),
                    "response": message["content"],
                    "confidence": message.get("confidence", 0.5),
                    "metadata": {"manual": True},
                },
            )
            st.success(f"Escalated with queue ID {response['item_id']}")

user_query = st.chat_input("Ask ChatSarathi anything")
if user_query:
    st.session_state.messages.append({"id": len(st.session_state.messages) + 1, "role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        placeholder = st.empty()

        def update_stream(content: str) -> None:
            placeholder.markdown(content + "|")

        final = run_async(stream_chat(st.session_state.session_id, user_query, on_token=update_stream))
        placeholder.markdown(final["response"])
        render_sources(final.get("rag_sources", []))

    st.session_state.messages.append(
        {
            "id": len(st.session_state.messages) + 1,
            "role": "assistant",
            "content": final["response"],
            "sources": final.get("rag_sources", []),
            "confidence": final.get("confidence", 0.0),
            "query": user_query,
        }
    )
