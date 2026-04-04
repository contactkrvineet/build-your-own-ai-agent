# Vineet AI AGENT

> A production-grade AI Agent showcasing advanced AI engineering — built for [vineetkr.com](https://vineetkr.com)

---

## What Is Vineet AI AGENT ?

Vineet AI AGENT is a modular, configurable AI agent that answers questions about using RAG over personal documents, connects to external APIs (weather, Gmail, Calendar), and runs automated workflows — all with a single config change to swap LLM provider.

**Built to demonstrate**: LLM abstraction, RAG pipelines, ReAct tool-use, workflow automation, FastAPI, Streamlit, Docker, and SDET-focused LLM I/O validation testing.

---

## Key Features

| Feature               | Description                                                                                               |
| --------------------- | --------------------------------------------------------------------------------------------------------- |
| **6 LLM Providers**   | OpenAI, Anthropic, Groq, Gemini, Ollama (local), HuggingFace — switch via `config.yaml`, zero code change |
| **RAG Pipeline**      | Indexes PDF, TXT, DOCX, Markdown with OCR fallback for scanned documents                                  |
| **ReAct Agent**       | Reason + Act loop with pluggable tools (Weather, Gmail, Calendar, Custom REST)                            |
| **Workflow System**   | Scheduled (cron), File-event, and Manual YAML pipeline triggers                                           |
| **FastAPI Backend**   | REST + WebSocket endpoints with Pydantic-validated schemas                                                |
| **Streamlit UI**      | Black/green terminal aesthetic chat interface                                                             |
| **Embeddable Widget** | Vanilla HTML/JS widget for portfolio site embedding                                                       |
| **Hot Reload**        | Drop a new document → indexed in seconds, no restart needed                                               |
| **Docker Ready**      | Multi-stage Dockerfile + docker-compose for one-command deployment                                        |
| **SDET Test Suite**   | Unit, integration, and LLM I/O validation with `LLMOutputValidator` fluent API                            |

---

## Quick Start (5 minutes)

```bash
# 1. Enter project
cd /path/to/AgentVineet

# 2. Create virtualenv and install
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure (minimum: one LLM key)
cp .env.example .env
echo "GROQ_API_KEY=gsk_YOUR_KEY" >> .env    # Free at console.groq.com

# 4. Add your documents (optional)
cp ~/Downloads/document.pdf documents/

# 5. Start API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# 6. Start UI
streamlit run ui/streamlit_app.py --server.port 8501
```

Open **http://localhost:8501** → start chatting.

For the complete step-by-step guide see [EXECUTION.md](EXECUTION.md).

---

## Switching LLM Provider

Edit `.env` only:

```bash
# Groq (fast, free tier)
LLM_PROVIDER=groq
LLM_MODEL=llama3-8b-8192
GROQ_API_KEY=gsk_...

# OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# Claude
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

# Fully local (no API key)
LLM_PROVIDER=ollama
LLM_MODEL=llama3
```

Restart the API — no Python code changes.

---

## Project Structure

```
AgentVineet/
├── app/
│   ├── agent/          # Core agent: router, memory, prompts, ReAct loop
│   ├── api/            # FastAPI routes: chat, documents, health
│   ├── config/         # Pydantic Settings — reads .env + config.yaml
│   ├── llm/            # LiteLLM wrapper + LangChain adapter + factory
│   ├── rag/            # Ingestion, chunking, embeddings, vector store, retriever
│   ├── tools/          # Weather, Gmail, Calendar, Custom API tools
│   ├── utils/          # Logger, OCR helpers
│   ├── workflows/      # Scheduler, file watcher, YAML pipeline executor
│   └── main.py         # FastAPI app with lifespan
├── ui/
│   ├── streamlit_app.py        # Black/green Streamlit chat app
│   └── static/                 # Embeddable HTML/CSS/JS widget
├── tests/
│   ├── test_agent/             # Agent core + router unit tests
│   ├── test_api/               # FastAPI endpoint tests
│   ├── test_llm/               # LLM provider + factory tests
│   ├── test_rag/               # Ingestion + retriever tests
│   ├── test_tools/             # Tool enable/disable + HTTP mock tests
│   └── test_validation/        # LLM I/O validation framework (SDET showcase)
├── workflows/
│   ├── scheduled_jobs.yaml     # Cron job definitions
│   └── sample_workflow.yaml    # Multi-step pipeline example
├── documents/                  # Drop your PDFs/TXTs here
├── data/                       # Auto-created: vectorstore, logs
├── config.yaml                 # Master config (non-secret settings)
├── .env.example                # All required environment variables
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── render.yaml                 # Render.com deployment (IaC)
├── pytest.ini
├── ARCHITECTURE.md             # Full system architecture + tech decisions
└── EXECUTION.md                # Complete step-by-step execution guide
```

---

## API Endpoints

| Method   | Path                         | Description                         |
| -------- | ---------------------------- | ----------------------------------- |
| `POST`   | `/chat/`                     | Send a message, get `AgentResponse` |
| `GET`    | `/chat/history/{session_id}` | Conversation history                |
| `DELETE` | `/chat/session/{session_id}` | Clear session                       |
| `WS`     | `/chat/ws/{session_id}`      | Streaming WebSocket chat            |
| `POST`   | `/documents/upload`          | Upload + index a file               |
| `GET`    | `/documents/list`            | List indexed files                  |
| `POST`   | `/documents/reload`          | Re-index all documents              |
| `GET`    | `/health/`                   | System health check                 |
| `GET`    | `/health/llm`                | LLM provider reachability           |

Interactive docs: **http://localhost:8000/docs**

---

## Accessible URLs

### Local Development

| Service             | URL                                      | Description                           |
| ------------------- | ---------------------------------------- | ------------------------------------- |
| **Streamlit UI**    | http://localhost:8501                    | Chat interface                        |
| **FastAPI Backend** | http://localhost:8000                    | REST API base                         |
| **Swagger Docs**    | http://localhost:8000/docs               | Interactive API docs (auto-generated) |
| **ReDoc**           | http://localhost:8000/redoc              | Alternative API docs                  |
| **Health Check**    | http://localhost:8000/health/            | System status                         |
| **LLM Health**      | http://localhost:8000/health/llm         | LLM provider reachability             |
| **WebSocket Chat**  | ws://localhost:8000/chat/ws/{session_id} | Real-time streaming chat              |

### Docker (`docker compose up`)

Same URLs as local — ports `8000` (API) and `8501` (UI) are mapped by default.

### Render.com (Production)

| Service            | URL                                                   | Notes                                |
| ------------------ | ----------------------------------------------------- | ------------------------------------ |
| **API**            | https://askvineet-api.onrender.com                    | FastAPI backend                      |
| **UI**             | https://askvineet-ui.onrender.com                     | Streamlit chat app                   |
| **Swagger Docs**   | https://askvineet-api.onrender.com/docs               | Live interactive docs                |
| **Health Check**   | https://askvineet-api.onrender.com/health/            | Used by Render for health monitoring |
| **WebSocket Chat** | wss://askvineet-api.onrender.com/chat/ws/{session_id} | Secure streaming in production       |

> **Note**: Free-tier Render services spin down after 15 min idle. The first request after spin-down takes ~30-60 seconds to cold-start.

---

## Running Tests

```bash
# All unit tests (fully mocked, no LLM key needed)
pytest tests/ -v -m "not live"

# LLM I/O validation showcase
pytest tests/test_validation/ -v

# With coverage
pytest tests/ -m "not live" --cov=app --cov-report=term-missing

# Live tests (require real API key)
pytest tests/ -m live -v
```

### LLM I/O Validation (`LLMOutputValidator`)

```python
# Fluent assertion API — readable SDET-style test intent
LLMOutputValidator(response)
    .not_empty()
    .min_length(20)
    .max_length(4000)
    .contains("AskVineet")
    .not_contains("sk-", "api_key")   # No secret leakage
    .routed_via("direct")
    .assert_all()
```

---

## Docker Deployment

```bash
docker compose build
docker compose up -d

# API  → http://localhost:8000
# UI   → http://localhost:8501
# Docs → http://localhost:8000/docs

docker compose down
```

### Deploy to Render (Free)

1. Sign up at [render.com](https://render.com) (free, no credit card).
2. **New → Blueprint** → connect your GitHub repo.
3. Render detects `render.yaml` and creates both services automatically.
4. Add `GROQ_API_KEY` in the Render dashboard under each service's **Environment**.
5. Hit **Deploy** — your app is live.

To enable GitHub Actions auto-deploy:

1. In Render dashboard → each service → **Settings → Deploy Hook** → copy the URL.
2. In GitHub → **Settings → Secrets → Actions** → add:
   - `RENDER_DEPLOY_HOOK_API` — the API service deploy hook URL
   - `RENDER_DEPLOY_HOOK_UI` — the UI service deploy hook URL (optional)

---

## How It Works

1. **User sends message** → FastAPI receives it.
2. **Router classifies query** → `direct` (plain LLM), `rag` (document search), or `tool` (external API).
3. **RAG path**: query → embed → ChromaDB similarity search → top-5 chunks → LLM synthesises answer with sources.
4. **Tool path**: ReAct agent (`Thought → Action → Observation`) loop through enabled tools.
5. **Direct path**: message + session history → LLM → response.
6. **Session memory** (last 10 turns) is attached to every call.
7. Response (answer + route + sources + token count) returned to client.

See [ARCHITECTURE.md](ARCHITECTURE.md) for full diagrams and data flow.

---

## What Can You Ask?

The agent **auto-detects intent** and routes each query to the right path:

### RAG Queries — Ask about uploaded documents

> "Tell me about Vineet's experience"  
> "What projects are in his portfolio?"  
> "Summarize his resume"  
> "What skills does Vineet have?"  
> "What certifications does he hold?"

**Trigger keywords**: document, file, PDF, resume, portfolio, Vineet, skills, projects

### Tool Queries — Get live data

| Tool           | Example Prompts                                                  |
| -------------- | ---------------------------------------------------------------- |
| **Weather**    | "What's the weather in London?", "Temperature in San Francisco?" |
| **Gmail**      | "Check my unread emails", "Summarize my inbox"                   |
| **Calendar**   | "What's on my calendar tomorrow?", "Show my upcoming meetings"   |
| **Custom API** | "Fetch data from my API"                                         |

**Trigger keywords**: weather, temperature, email, gmail, calendar, schedule, API, fetch

### Direct Queries — General LLM knowledge

> "Explain OAuth2"  
> "How do I debug a Python async function?"  
> "What is a ReAct agent?"  
> "Hi, how are you?"

Any query that doesn't match RAG or tool keywords goes straight to the LLM.

---

## Tech Stack

| Layer           | Technology              | Why                                        |
| --------------- | ----------------------- | ------------------------------------------ |
| Agent framework | LangChain 0.3           | Mature, LCEL, tool ecosystem               |
| LLM abstraction | LiteLLM 1.44            | 100+ providers, zero code change to switch |
| Vector store    | ChromaDB 0.5            | Auto-persist, metadata filtering           |
| Embeddings      | sentence-transformers   | Free, local, no API key                    |
| API             | FastAPI 0.114           | Async, auto-docs, WebSocket, Pydantic      |
| Scheduler       | APScheduler 3.10        | No broker required                         |
| File watcher    | watchdog <5.0           | Cross-platform inotify wrapper             |
| UI              | Streamlit 1.38          | Python-native rapid UI                     |
| Config          | Pydantic Settings 2.5   | Type-safe, env override                    |
| Testing         | pytest + pytest-asyncio | Standard, async support                    |
| Logging         | Loguru                  | Structured JSON + console                  |
| OCR             | pytesseract + pdf2image | Scanned PDF fallback                       |

---

## License

MIT — use freely for portfolio, learning, or as a starter template.

---

_Built by Vineet Kumar · [vineetkr.com](https://vineetkr.com)_
