"""LLM orchestration service for ChatSarathi."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama

from app.config import ChatSarathiError, ExternalServiceError, settings
from app.memory.memory_manager import memory_manager
from app.services.rag_service import RetrievalBundle, rag_service
from app.tools import ArxivTool, TavilyTool, WikiTool


@dataclass(slots=True)
class LLMResponse:
    """Normalized response returned by the LLM service."""

    session_id: str
    response_text: str
    model_name: str
    model_version: str
    tools_used: list[str] = field(default_factory=list)
    rag_sources: list[dict[str, Any]] = field(default_factory=list)
    hitl_confidence: float = 1.0
    retrieval_bundle: RetrievalBundle | None = None


class LLMService:
    """Coordinate RAG, tool use, memory, and streaming generation."""

    def __init__(self) -> None:
        """Initialize the configured LLM provider and tool bindings."""
        self._provider = settings.llm_provider.strip().lower()
        self._anthropic: AsyncAnthropic | None = None
        self._planner: ChatAnthropic | ChatOllama | None = None
        self._bound_planner = None
        self._model_name = settings.ollama_model
        self._model_version = "ollama-local"

        if self._provider == "anthropic":
            if not settings.anthropic_api_key:
                raise ExternalServiceError(
                    "LLM_PROVIDER is set to 'anthropic' but ANTHROPIC_API_KEY is missing.",
                    code="anthropic_api_key_missing",
                )
            self._anthropic = AsyncAnthropic(api_key=settings.anthropic_api_key)
            self._planner = ChatAnthropic(
                model=settings.anthropic_model,
                anthropic_api_key=settings.anthropic_api_key,
                temperature=0.2,
                streaming=True,
            )
            self._model_name = settings.anthropic_model
            self._model_version = settings.anthropic_model_version
        elif self._provider == "ollama":
            self._planner = ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=0.2,
                streaming=True,
            )
        else:
            raise ExternalServiceError(
                f"Unsupported LLM provider: {settings.llm_provider}",
                code="unsupported_llm_provider",
                details={"provider": settings.llm_provider},
            )

        self._arxiv_tool = ArxivTool()
        self._wiki_tool = WikiTool()
        self._tavily_tool = TavilyTool()
        self._langchain_tools = [
            self._arxiv_tool.as_langchain_tool(),
            self._wiki_tool.as_langchain_tool(),
            self._tavily_tool.as_langchain_tool(),
        ]
        if self._planner is not None:
            self._bound_planner = self._planner.bind_tools(self._langchain_tools)
        self._tool_map = {
            self._arxiv_tool.name: self._arxiv_tool.search,
            self._wiki_tool.name: self._wiki_tool.search,
            self._tavily_tool.name: self._tavily_tool.search,
        }

    async def generate(self, session_id: str, query: str) -> LLMResponse:
        """Generate a synchronous response for the given session.

        Args:
            session_id: Conversation session identifier.
            query: User input.

        Returns:
            Fully assembled response payload.
        """
        chunks: list[str] = []
        response_payload: LLMResponse | None = None
        async for event in self.generate_stream(session_id, query):
            if event["type"] == "token":
                chunks.append(event["content"])
            elif event["type"] == "complete":
                response_payload = event["payload"]
        if response_payload is None:
            raise ExternalServiceError("LLM response generation failed.", code="llm_generation_failed")
        response_payload.response_text = "".join(chunks).strip() or response_payload.response_text
        return response_payload

    async def generate_stream(self, session_id: str, query: str) -> AsyncIterator[dict[str, Any]]:
        """Stream an answer token-by-token.

        Args:
            session_id: Conversation session identifier.
            query: User input.

        Yields:
            Streaming events containing tokens and final metadata.
        """
        is_code_request = self._is_code_request(query)
        is_simple_chat = self._is_simple_chat_request(query)
        retrieval = await rag_service.retrieve(query) if not (is_code_request or is_simple_chat) else RetrievalBundle(
            context_text="",
            local_results=[],
            external_results={},
        )
        history = await memory_manager.get_recent_history(session_id)
        messages = self._build_react_messages(history, retrieval, query)
        tools_used: list[str] = []
        tool_transcript = ""

        if self._bound_planner is not None and not (is_code_request or is_simple_chat):
            for _ in range(2):
                planner_message = await self._bound_planner.ainvoke(messages)
                messages.append(planner_message)
                tool_calls = getattr(planner_message, "tool_calls", [])
                if not tool_calls:
                    break
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    args = tool_call.get("args", {})
                    result = await self._execute_tool(tool_name, args)
                    tools_used.append(tool_name)
                    tool_transcript += f"\nTool {tool_name} output:\n{result}\n"
                    messages.append(ToolMessage(content=json.dumps(result), tool_call_id=tool_call["id"]))

        final_prompt = self._build_final_prompt(
            history,
            retrieval,
            query,
            tool_transcript,
            is_code_request=is_code_request,
            is_simple_chat=is_simple_chat,
        )
        response_text = ""

        try:
            if self._provider == "ollama":
                if self._planner is None:
                    raise ExternalServiceError("Ollama planner is not initialized.", code="ollama_planner_missing")
                async for chunk in self._planner.astream(final_prompt["messages"]):
                    text_chunk = self._coerce_text_content(chunk.content)
                    if not text_chunk:
                        continue
                    response_text += text_chunk
                    yield {"type": "token", "content": text_chunk}
            else:
                if self._anthropic is None:
                    raise ExternalServiceError("Anthropic client is not initialized.", code="anthropic_client_missing")
                async with self._anthropic.messages.stream(
                    model=settings.anthropic_model,
                    max_tokens=900,
                    temperature=0.2,
                    system=final_prompt["system"],
                    messages=final_prompt["messages"],
                ) as stream:
                    async for text in stream.text_stream:
                        response_text += text
                        yield {"type": "token", "content": text}
        except ExternalServiceError:
            raise
        except Exception as exc:
            raise ExternalServiceError(
                f"Failed to generate a response using the configured {self._provider} model.",
                code="llm_backend_unavailable",
                details={
                    "provider": self._provider,
                    "model": self._model_name,
                    "reason": str(exc),
                },
            ) from exc

        confidence = self.estimate_confidence(response_text, retrieval, tools_used)
        rag_sources = [
            {
                "label": item.metadata.get("source", item.source),
                "content": item.content,
                "score": item.score,
                "metadata": item.metadata,
            }
            for item in retrieval.local_results
        ]
        if retrieval.external_results.get("wiki"):
            rag_sources.append(
                {
                    "label": "Wikipedia",
                    "content": retrieval.external_results["wiki"].get("summary", ""),
                    "score": 0.5,
                    "metadata": retrieval.external_results["wiki"],
                }
            )
        payload = LLMResponse(
            session_id=session_id,
            response_text=response_text.strip(),
            model_name=self._model_name,
            model_version=self._model_version,
            tools_used=sorted(set(tools_used)),
            rag_sources=rag_sources,
            hitl_confidence=confidence,
            retrieval_bundle=retrieval,
        )
        await memory_manager.append_turn(session_id, query, response_text.strip())
        yield {"type": "complete", "payload": payload}

    def estimate_confidence(self, response_text: str, retrieval: RetrievalBundle, tools_used: list[str]) -> float:
        """Estimate confidence using simple uncertainty heuristics.

        Args:
            response_text: Generated answer text.
            retrieval: Retrieval bundle used for generation.
            tools_used: Tools invoked during reasoning.

        Returns:
            Confidence score between 0 and 1.
        """
        penalty = 0.0
        if not retrieval.local_results:
            penalty += 0.25
        if len(response_text.split()) < 30:
            penalty += 0.1
        if re.search(r"\b(might|maybe|uncertain|not sure|possibly)\b", response_text.lower()):
            penalty += 0.25
        if not tools_used and not retrieval.external_results.get("tavily"):
            penalty += 0.05
        return max(0.0, min(1.0, 0.92 - penalty))

    def _build_react_messages(
        self,
        history: list[dict[str, str]],
        retrieval: RetrievalBundle,
        query: str,
    ) -> list[Any]:
        system_prompt = (
            "You are ChatSarathi, a production-grade assistant. Reason carefully, use available tools when the answer "
            "benefits from fresh or specialized information, and ground answers in retrieved context with citations."
            f"\n\nRetrieved context:\n{retrieval.context_text}"
        )
        messages: list[Any] = [SystemMessage(content=system_prompt)]
        for item in history:
            if item["role"] == "user":
                messages.append(HumanMessage(content=item["content"]))
            else:
                messages.append(AIMessage(content=item["content"]))
        messages.append(HumanMessage(content=query))
        return messages

    def _build_final_prompt(
        self,
        history: list[dict[str, str]],
        retrieval: RetrievalBundle,
        query: str,
        tool_transcript: str,
        is_code_request: bool = False,
        is_simple_chat: bool = False,
    ) -> dict[str, Any]:
        history_lines = []
        for item in history:
            prefix = "User" if item["role"] == "user" else "Assistant"
            history_lines.append(f"{prefix}: {item['content']}")

        if is_code_request:
            system = (
                "You are ChatSarathi, a beginner-friendly coding assistant. "
                "For coding requests, return simple, complete, runnable code. "
                "Prefer clear multi-line solutions over short or clever one-liners. "
                "Use basic variables, if/else, loops, and input() when appropriate. "
                "Format code answers inside fenced Markdown code blocks with the correct language tag. "
                "Do not include sources unless the user explicitly asks for them."
            )
            user_content = (
                f"Conversation history:\n{chr(10).join(history_lines) or 'No prior history.'}\n\n"
                f"User query:\n{query}\n\n"
                "Return a beginner-friendly full program. Prefer input()-based code when it makes sense. "
                "Avoid lambda expressions, slicing tricks, and overly short answers unless the user explicitly asks for them. "
                "Keep explanation to zero or one short line."
            )
        elif is_simple_chat:
            system = (
                "You are ChatSarathi, a warm and concise assistant. "
                "For greetings, identity questions, and simple conversational requests, reply naturally as ChatSarathi. "
                "Do not use retrieval context or sources for simple chat unless the user asks for factual grounding."
            )
            user_content = (
                f"Conversation history:\n{chr(10).join(history_lines) or 'No prior history.'}\n\n"
                f"User query:\n{query}\n\n"
                "If the user asks your name or who you are, answer clearly that your name is ChatSarathi. "
                "Keep the reply short, natural, and conversational."
            )
        else:
            system = (
                "You are ChatSarathi, an intelligent assistant that follows the RICE architecture. "
                "Use the provided retrieval context and tool outputs. Cite sources inline using square brackets "
                "like [R1], [Wiki], [Arxiv 1], [Web 1] when relevant. If confidence is limited, say so clearly."
            )
            user_content = (
                f"Conversation history:\n{chr(10).join(history_lines) or 'No prior history.'}\n\n"
                f"Retrieved context:\n{retrieval.context_text}\n\n"
                f"Tool outputs:{tool_transcript or ' None'}\n\n"
                f"User query:\n{query}\n\n"
                "Respond with a direct, helpful answer followed by a short sources section if you used any."
            )
        return {"system": system, "messages": [{"role": "user", "content": user_content}]}
    async def _execute_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        query = args.get("query") if isinstance(args, dict) else None
        if not query:
            return {"error": "Missing query parameter."}
        handler = self._tool_map.get(tool_name)
        if handler is None:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return await handler(query)
        except ChatSarathiError as exc:
            return {
                "error": exc.message,
                "code": exc.code,
                "details": exc.details,
                "tool": tool_name,
            }
        except Exception as exc:
            return {
                "error": f"Tool execution failed: {tool_name}",
                "details": {"reason": str(exc)},
                "tool": tool_name,
            }

    def _coerce_text_content(self, content: Any) -> str:
        """Normalize LangChain model output content into plain text."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                else:
                    parts.append(str(item))
            return "".join(parts)
        return str(content)

    def _stream_text_chunks(self, text: str) -> list[str]:
        """Preserve whitespace while simulating streamed chunks for non-streaming backends."""
        chunks = re.findall(r"\S+\s*|\s+", text)
        return chunks or ([text] if text else [])

    def _is_simple_chat_request(self, query: str) -> bool:
        """Detect greetings and identity questions that should skip retrieval."""
        normalized = re.sub(r"[^a-z0-9\s]", " ", query.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        simple_phrases = {
            "hi",
            "hello",
            "hey",
            "good morning",
            "good evening",
            "what is your name",
            "whats your name",
            "who are you",
            "tell me your name",
            "your name",
            "introduce yourself",
        }
        return normalized in simple_phrases

    def _is_code_request(self, query: str) -> bool:
        """Detect simple code-generation requests to avoid noisy retrieval output."""
        normalized = query.lower()
        code_markers = (
            "write code",
            "write python code",
            "give code",
            "only code",
            "program for",
            "python code",
            "java code",
            "c++ code",
            "javascript code",
            "code for",
            "function for",
            "implement",
        )
        return any(marker in normalized for marker in code_markers)

    def _offline_fallback(self, query: str, retrieval: RetrievalBundle) -> str:
        snippets = [f"[R{idx}] {item.content}" for idx, item in enumerate(retrieval.local_results, start=1)]
        if retrieval.external_results.get("wiki"):
            snippets.append(f"[Wiki] {retrieval.external_results['wiki'].get('summary', '')}")
        if not snippets:
            snippets.append("No indexed knowledge is available yet.")
        return (
            "ChatSarathi could not reach the configured LLM backend, so this is a retrieval-based fallback answer.\n\n"
            f"Your question was: {query}\n\n"
            "Relevant context:\n"
            + "\n".join(snippets[:5])
        )


llm_service = LLMService()
