"""Seed the ChatSarathi vector store with sample documents."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.models.vectorstore_manager import vectorstore_manager


SAMPLE_DOCUMENTS = [
    {
        "id": "doc-architecture",
        "content": (
            "ChatSarathi follows the RICE architecture: Retrieval with hybrid search, Intelligence with "
            "tool-augmented LLM orchestration, Conversation memory with Redis, and Execution analytics."
        ),
        "metadata": {"source": "internal_architecture", "category": "architecture"},
    },
    {
        "id": "doc-deployment",
        "content": (
            "ChatSarathi is deployed with FastAPI, Streamlit, Redis, and ChromaDB. Kubernetes deployment uses "
            "two replicas, resource limits, and horizontal pod autoscaling."
        ),
        "metadata": {"source": "deployment_guide", "category": "ops"},
    },
    {
        "id": "doc-hitl",
        "content": (
            "Human-in-the-loop escalation is triggered when model confidence falls below the configured "
            "threshold, enabling pending, resolved, and dismissed review states."
        ),
        "metadata": {"source": "hitl_policy", "category": "safety"},
    },
]


async def main() -> None:
    """Reset and seed the vector store with baseline documents."""
    Path("chroma_db").mkdir(exist_ok=True)
    await vectorstore_manager.reset_collection()
    await vectorstore_manager.batch_upsert(SAMPLE_DOCUMENTS)
    print("Vector store initialized with sample documents.")


if __name__ == "__main__":
    asyncio.run(main())
