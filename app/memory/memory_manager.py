"""Session memory management with Redis-backed persistence."""

from __future__ import annotations

import json

try:
    from langchain_classic.memory import ConversationBufferWindowMemory
except ImportError:  # pragma: no cover - fallback for older LangChain installs
    from langchain.memory import ConversationBufferWindowMemory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from redis.asyncio import Redis

from app.config import logger, settings


class MemoryManager:
    """Manage per-session conversation memory in Redis and LangChain."""

    def __init__(self) -> None:
        """Initialize Redis connectivity and in-memory session cache."""
        self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self._memories: dict[str, ConversationBufferWindowMemory] = {}

    async def get_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        """Fetch or rebuild the memory object for a session.

        Args:
            session_id: Session identifier.

        Returns:
            Windowed LangChain conversation memory.
        """
        if session_id in self._memories:
            return self._memories[session_id]
        memory = ConversationBufferWindowMemory(
            k=settings.memory_window,
            memory_key="chat_history",
            return_messages=True,
            input_key="input",
            output_key="output",
        )
        history = await self._load_history(session_id)
        for item in history:
            if item["role"] == "user":
                memory.chat_memory.add_message(HumanMessage(content=item["content"]))
            else:
                memory.chat_memory.add_message(AIMessage(content=item["content"]))
        self._memories[session_id] = memory
        return memory

    async def append_turn(self, session_id: str, user_message: str, assistant_message: str) -> None:
        """Append a completed conversation turn.

        Args:
            session_id: Session identifier.
            user_message: User message text.
            assistant_message: Assistant response text.
        """
        memory = await self.get_memory(session_id)
        memory.chat_memory.add_user_message(user_message)
        memory.chat_memory.add_ai_message(assistant_message)
        await self._persist_history(session_id, memory.chat_memory.messages)

    async def get_recent_history(self, session_id: str) -> list[dict[str, str]]:
        """Return recent serialized conversation history.

        Args:
            session_id: Session identifier.

        Returns:
            Serialized message list.
        """
        history = await self._load_history(session_id)
        return history[-(settings.memory_window * 2) :]

    async def clear_session(self, session_id: str) -> None:
        """Clear a session from Redis and memory cache.

        Args:
            session_id: Session identifier.
        """
        self._memories.pop(session_id, None)
        await self._redis.delete(self._key(session_id))

    async def list_sessions(self) -> list[str]:
        """List known session IDs."""
        keys = await self._redis.keys("ChatSarathi:memory:*")
        return [key.split(":")[-1] for key in keys]

    async def _load_history(self, session_id: str) -> list[dict[str, str]]:
        key = self._key(session_id)
        raw = await self._redis.get(key)
        if not raw:
            return []
        return json.loads(raw)

    async def _persist_history(self, session_id: str, messages: list[BaseMessage]) -> None:
        serialized = [
            {"role": "user" if message.type == "human" else "assistant", "content": str(message.content)}
            for message in messages[-(settings.memory_window * 2) :]
        ]
        await self._redis.set(self._key(session_id), json.dumps(serialized))
        logger.info("memory.persisted", session_id=session_id, messages=len(serialized))

    @staticmethod
    def _key(session_id: str) -> str:
        return f"ChatSarathi:memory:{session_id}"


memory_manager = MemoryManager()

