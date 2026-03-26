# ChatSarathi

ChatSarathi is a production-oriented intelligent chatbot built with a RICE architecture:

- Retrieval: ChromaDB vector search, BM25 keyword search, Reciprocal Rank Fusion, and parallel external retrieval from arXiv, Wikipedia, and Tavily
- Intelligence: Claude Sonnet 4 orchestration, LangChain tool binding, ReAct-style tool loop, and retrieval-grounded prompting
- Conversation: Redis-backed session memory, WebSocket streaming, REST fallback, and HITL escalation
- Execution: SQLite analytics, Streamlit dashboard, Docker, and Kubernetes deployment assets

## Project Structure

```text
app/
  __init__.py
  main.py
  config.py
  routes/
    chat_routes.py
  services/
    __init__.py
    llm_service.py
    rag_service.py
    hitl_service.py
    analytics_service.py
  tools/
    __init__.py
    arxiv_tool.py
    wiki_tool.py
    tavily_tool.py
  memory/
    __init__.py
    memory_manager.py
  models/
    __init__.py
    vectorstore_manager.py
frontend/
  frontend.py
docker/
  Dockerfile
  docker-compose.yml
  k8s/
    deployment.yaml
    service.yaml
scripts/
  setup_vectorstore.py
requirements.txt
.env.example
README.md
```

## Features

- FastAPI backend with async REST and WebSocket chat endpoints
- Hybrid RAG with ChromaDB, sentence-transformers, BM25, and RRF fusion
- Tool-augmented reasoning with arXiv, Wikipedia, and Tavily
- Redis-backed `ConversationBufferWindowMemory` session memory
- HITL queue with confidence-based escalation and manual escalation API
- SQLite analytics with request latency, tools used, RAG sources, and model versioning
- Streamlit interface with live chat, source cards, analytics charting, and HITL queue display
- Docker multi-stage build, Docker Compose stack, Kubernetes Deployments, Services, and HPA

## Quick Start

1. Create and activate a Python 3.11+ virtual environment.
2. Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY` and `TAVILY_API_KEY`.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Seed the vector store:

```bash
python scripts/setup_vectorstore.py
```

5. Run the backend:

```bash
uvicorn app.main:app --reload
```

6. Run the frontend:

```bash
streamlit run frontend/frontend.py
```

## API Endpoints

- `GET /health`
- `POST /api/chat`
- `POST /api/hitl/escalate`
- `GET /api/hitl/queue`
- `GET /api/analytics/summary`
- `GET /api/sessions`
- `GET /api/sessions/{session_id}/history`
- `WS /api/ws/chat/{session_id}`

## Architecture Notes

### Retrieval

`app/services/rag_service.py` combines:

- ChromaDB similarity search with `sentence-transformers/all-MiniLM-L6-v2`
- BM25 keyword search using `rank_bm25`
- Reciprocal Rank Fusion for score merging
- Parallel external retrieval from arXiv, Wikipedia, and Tavily

### Intelligence

`app/services/llm_service.py` uses:

- `langchain-anthropic` for tool planning with `bind_tools()`
- `anthropic` SDK streaming for final answer generation
- ReAct-style tool execution loop
- Retrieval context injection with inline citation guidance

### Conversation

`app/memory/memory_manager.py` provides:

- `ConversationBufferWindowMemory` for last-10-turn context
- Redis persistence of serialized chat history
- Session listing and replay support

### Execution

`app/services/analytics_service.py` and `frontend/frontend.py` provide:

- Async SQLite analytics via SQLAlchemy
- Session-level dashboarding in Streamlit with Altair charts
- HITL queue visibility and manual escalation workflow

## Docker

Run the full stack with:

```bash
docker compose -f docker/docker-compose.yml up --build
```

## Kubernetes

Apply the manifests:

```bash
kubectl apply -f docker/k8s/deployment.yaml
kubectl apply -f docker/k8s/service.yaml
```

## Notes

- When `ANTHROPIC_API_KEY` is not configured, ChatSarathi falls back to retrieval-grounded offline responses so the app can still boot and be demoed locally.
- Tavily gracefully degrades when `TAVILY_API_KEY` is missing.
- The analytics database defaults to `./ChatSarathi_analytics.db`.
- Here I set up local ollama llama3.2:3b  for local setup 
