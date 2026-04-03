# AskVineet — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AskVineet System                             │
│                                                                     │
│  ┌──────────┐   ┌──────────────────────┐   ┌───────────────────┐  │
│  │Streamlit │   │  Embeddable Widget   │   │  External Client  │  │
│  │   Chat   │   │  (HTML/CSS/JS)       │   │  (Portfolio Site) │  │
│  └────┬─────┘   └──────────┬───────────┘   └────────┬──────────┘  │
│       │                    │                         │              │
│       └──────────┬─────────┘                         │              │
│                  │  HTTP REST / WebSocket             │              │
│                  ▼                                    ▼              │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                  FastAPI Backend (app/main.py)                │  │
│  │  POST /chat/   GET /chat/history/{id}   WS /chat/ws/{id}     │  │
│  │  POST /documents/upload   GET /documents/list                 │  │
│  │  GET /health/   GET /health/llm                               │  │
│  └─────────────────────────┬─────────────────────────────────────┘  │
│                             │                                        │
│                             ▼                                        │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                  AskVineet Agent Core                         │  │
│  │                                                               │  │
│  │   User Query                                                  │  │
│  │       │                                                       │  │
│  │       ▼                                                       │  │
│  │  ┌──────────┐   keyword + LLM classifier                     │  │
│  │  │  Router  ├──────────────┬──────────────┐                  │  │
│  │  └──────────┘              │              │                  │  │
│  │        │                   │              │                  │  │
│  │        ▼                   ▼              ▼                  │  │
│  │  ┌──────────┐   ┌──────────────┐  ┌──────────────┐          │  │
│  │  │  Direct  │   │  RAG Chain   │  │ ReAct Agent  │          │  │
│  │  │   LLM    │   │ (documents)  │  │   (tools)    │          │  │
│  │  └────┬─────┘   └──────┬───────┘  └──────┬───────┘          │  │
│  │       │                │                  │                  │  │
│  │       └────────────────┼──────────────────┘                  │  │
│  │                        │                                      │  │
│  │                        ▼                                      │  │
│  │              ┌──────────────────┐                            │  │
│  │              │ Session Memory   │                            │  │
│  │              │ (ConvBufferWin)  │                            │  │
│  │              └──────────────────┘                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────┐  ┌──────────────────────────────────────┐  │
│  │   LLM Layer         │  │   RAG Pipeline                       │  │
│  │                     │  │                                      │  │
│  │  LiteLLMProvider    │  │  documents/ ──► Ingestion            │  │
│  │  (unified API)      │  │  PDF,TXT,DOCX,MD (+ OCR)            │  │
│  │                     │  │       │                              │  │
│  │  ┌──────────────┐   │  │       ▼                              │  │
│  │  │ openai/...   │   │  │  RecursiveCharacter Splitter         │  │
│  │  │ anthropic/.. │   │  │       │                              │  │
│  │  │ groq/...     │   │  │       ▼                              │  │
│  │  │ gemini/...   │   │  │  HuggingFace Embeddings              │  │
│  │  │ ollama/...   │   │  │  (all-MiniLM-L6-v2, local)          │  │
│  │  │ huggingface/ │   │  │       │                              │  │
│  │  └──────────────┘   │  │       ▼                              │  │
│  └─────────────────────┘  │  ChromaDB / FAISS VectorStore        │  │
│                            │       │                              │  │
│  ┌─────────────────────┐  │       ▼                              │  │
│  │   Tools (Plug-in)   │  │  Similarity Search → Top-K Docs     │  │
│  │                     │  │       │                              │  │
│  │  🌤 WeatherTool      │  │       ▼                              │  │
│  │  📧 GmailTool        │  │  RetrievalQA Chain → Answer         │  │
│  │  📅 CalendarTool     │  └──────────────────────────────────────┘  │
│  │  🔌 CustomAPITool    │                                            │
│  └─────────────────────┘                                            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │   Workflow & Trigger System                                  │    │
│  │                                                             │    │
│  │  Manual ──────────────┐                                     │    │
│  │  (REST call / CLI)    │                                     │    │
│  │                       ▼                                     │    │
│  │  Scheduled ──────► Pipeline ──► Agent ──► Output / Log     │    │
│  │  (APScheduler)        ▲                                     │    │
│  │                       │                                     │    │
│  │  File Drop ───────────┘                                     │    │
│  │  (Watchdog)     → also triggers hot-reload indexing         │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Layer-by-Layer Explanation

### 1. LLM Layer — `app/llm/`

| Component            | File                 | Purpose                                                             |
| -------------------- | -------------------- | ------------------------------------------------------------------- |
| `BaseLLMProvider`    | `base.py`            | Abstract interface — callers never depend on a concrete provider    |
| `LiteLLMProvider`    | `litellm_wrapper.py` | Implements the interface using LiteLLM, covering 100+ providers     |
| `AskVineetChatModel` | `litellm_wrapper.py` | LangChain `BaseChatModel` subclass — plugs into any LangChain chain |
| `LLMFactory`         | `factory.py`         | Reads config/env and constructs the right provider instance         |

**Why LiteLLM?**

- Single function (`litellm.completion`) works for OpenAI, Anthropic, Groq, Gemini, Ollama, HuggingFace.
- Zero code change to switch provider — only `config.yaml` needs editing.
- Built-in retry, timeout, and cost-tracking capabilities.

**Provider model string mapping:**

| Provider    | Config value  | LiteLLM model string                       |
| ----------- | ------------- | ------------------------------------------ |
| Groq        | `groq`        | `groq/llama3-8b-8192`                      |
| OpenAI      | `openai`      | `gpt-4o`                                   |
| Anthropic   | `anthropic`   | `claude-3-5-sonnet-20241022`               |
| Gemini      | `gemini`      | `gemini/gemini-1.5-pro`                    |
| Ollama      | `ollama`      | `ollama/llama3`                            |
| HuggingFace | `huggingface` | `huggingface/HuggingFaceH4/zephyr-7b-beta` |

---

### 2. RAG Pipeline — `app/rag/`

```
documents/              ← Drop files here
    │
    ▼
ingestion.py            ← Loads PDF (+ OCR), TXT, DOCX, MD
    │
    ▼
chunker.py              ← RecursiveCharacterTextSplitter
    │   chunk_size=1000, chunk_overlap=200
    ▼
embeddings.py           ← HuggingFace all-MiniLM-L6-v2 (local, free)
    │
    ▼
vectorstore.py          ← ChromaDB (default) or FAISS
    │   Persisted to data/vectorstore/
    ▼
retriever.py            ← RetrievalQA chain
    │   Returns top-5 chunks + LLM-synthesised answer
    ▼
AgentResponse.sources   ← Source metadata shown to user
```

**Why ChromaDB over FAISS?**

- ChromaDB auto-persists to disk; FAISS requires manual `save_local()`.
- ChromaDB supports metadata filtering out of the box.
- Both are supported — switch via `config.yaml → rag.vector_store`.

**OCR Flow:**

1. pypdf attempts text extraction from every PDF page.
2. If a page yields < 100 chars (scanned), pytesseract + pdf2image is used.
3. OCR can be globally toggled: `config.yaml → rag.ocr_enabled`.

**Hot-Reload:**

1. Watchdog monitors `documents/` for new/modified files.
2. On event, `agent.add_document(path)` chunks + embeds the file.
3. New chunks are appended to the existing vector store — no full rebuild.

---

### 3. Agent Core — `app/agent/`

#### Router Decision Tree

```
                    User Query
                        │
            ┌───────────▼───────────┐
            │  Short greeting?       │──YES──► DIRECT
            └───────────┬───────────┘
                        │
            ┌───────────▼───────────┐
            │  Tool keyword match?   │──YES──► TOOL
            │  (weather, email, ...) │
            └───────────┬───────────┘
                        │
            ┌───────────▼───────────┐
            │  RAG keyword match?    │──YES──► RAG (if enabled)
            │  (document, Vineet,..) │
            └───────────┬───────────┘
                        │
            ┌───────────▼───────────┐
            │  LLM classification    │──────► RAG | TOOL | DIRECT
            └───────────────────────┘
```

#### ReAct Agent (Tool use)

Uses LangChain's `create_react_agent` with the classic ReAct loop:

```
Thought → Action → Action Input → Observation → (repeat) → Final Answer
```

Tools are loaded dynamically — only enabled tools (per config) are registered.

#### Memory

- **Short-term**: `ConversationBufferWindowMemory(k=10)` — last 10 turns per session.
- Sessions are keyed by `session_id` (UUID). New UUID = fresh conversation.
- **Long-term** (planned): Append important facts to the vector store.

---

### 4. Tools — `app/tools/`

| Tool        | Class           | Config Toggle              | Auth                               |
| ----------- | --------------- | -------------------------- | ---------------------------------- |
| Weather     | `WeatherTool`   | `tools.weather.enabled`    | `OPENWEATHERMAP_API_KEY`           |
| Gmail       | `GmailTool`     | `tools.gmail.enabled`      | `GOOGLE_CREDENTIALS_FILE` (OAuth2) |
| Calendar    | `CalendarTool`  | `tools.calendar.enabled`   | `GOOGLE_CREDENTIALS_FILE` (OAuth2) |
| Custom REST | `CustomAPITool` | `tools.custom_api.enabled` | `CUSTOM_API_KEY`                   |

All tools extend `AskVineetBaseTool → langchain_core.tools.BaseTool`.
The ReAct agent receives whichever tools pass `is_enabled()`.

---

### 5. Workflow System — `app/workflows/`

| Component         | File              | Trigger type                     |
| ----------------- | ----------------- | -------------------------------- |
| APScheduler       | `scheduler.py`    | Cron-style scheduled             |
| Watchdog          | `file_watcher.py` | File creation/modification event |
| Pipeline executor | `pipeline.py`     | Any (reads YAML definition)      |

**Pipeline YAML structure:**

```yaml
name: "My Workflow"
trigger:
  type: scheduled
  cron: "0 9 * * *"
steps:
  - action: query_agent
    input: "Summarise today's documents"
  - action: log
    message: "Done"
  - action: http_request
    url: "https://hooks.example.com/webhook"
    method: POST
    payload: { "text": "{{prev}}" }
```

---

### 6. API Layer — `app/api/`

| Endpoint             | Method    | Description                       |
| -------------------- | --------- | --------------------------------- |
| `/chat/`             | POST      | Send message, get `AgentResponse` |
| `/chat/history/{id}` | GET       | Conversation history for session  |
| `/chat/session/{id}` | DELETE    | Clear session memory              |
| `/chat/ws/{id}`      | WebSocket | Real-time streaming chat          |
| `/documents/upload`  | POST      | Upload + immediately index file   |
| `/documents/list`    | GET       | List indexed documents            |
| `/documents/reload`  | POST      | Re-index all documents            |
| `/health/`           | GET       | System health                     |
| `/health/llm`        | GET       | LLM provider reachability         |

---

### 7. UI — `ui/`

**Streamlit App** (`streamlit_app.py`):

- Calls the FastAPI backend via HTTP (decoupled design).
- Black `#000000` background, neon green `#00FF41` text.
- Monospace `Courier New` font — terminal aesthetic.
- Custom CSS injected via `st.markdown(unsafe_allow_html=True)`.
- Shows RAG sources in collapsible expander.
- Sidebar: new conversation, document upload, API health check.

**Embeddable Widget** (`ui/static/`):

- Vanilla HTML/CSS/JS — no framework dependencies.
- Connects to FastAPI REST endpoint.
- Embeddable in any website via `<iframe>` or direct HTML include.
- Same black/green terminal theme.

---

### 8. Testing — `tests/`

| Test Module                      | Scope       | What it validates                                     |
| -------------------------------- | ----------- | ----------------------------------------------------- |
| `test_agent/test_core.py`        | Unit        | Agent init, response shape, session continuity        |
| `test_agent/test_router.py`      | Unit        | Routing decisions by keyword                          |
| `test_llm/test_providers.py`     | Unit        | LLM response parsing, token counts, factory           |
| `test_rag/test_ingestion.py`     | Unit        | File loading, metadata, empty files                   |
| `test_rag/test_retriever.py`     | Unit        | Chunking, similarity search calls                     |
| `test_tools/test_tools.py`       | Unit        | Tool enable/disable, HTTP mocking                     |
| `test_api/test_chat.py`          | Integration | FastAPI endpoint schemas and status codes             |
| `test_validation/test_llm_io.py` | **SDET**    | Schema, content, hallucination, SLA, boundary, safety |

**LLM I/O Validation Framework** (`LLMOutputValidator`):

```python
# Fluent assertion style — readable test intent
LLMOutputValidator(response)
    .not_empty()
    .contains("AskVineet", "Vineet")
    .max_length(4000)
    .not_contains("sk-", "api_key")   # No secret leakage
    .routed_via("direct")
```

---

## Data Flow Diagram (RAG Query)

```
User: "What are Vineet's skills?"
         │
         ▼
Router classifies → "rag"
         │
         ▼
query → HuggingFace embed → [0.12, -0.34, ...]
         │
         ▼
ChromaDB cosine similarity search (top-5)
         │
         ▼
Retrieved chunks:
  [1] "Skills: Python, LangChain..." (score: 0.91)
  [2] "Projects: AskVineet..." (score: 0.87)
  [3] "Experience: 10+ years SDET..." (score: 0.85)
         │
         ▼
Prompt: "Context: {chunks}\nQuestion: What are Vineet's skills?"
         │
         ▼
LiteLLM → Groq API → llama3-8b-8192
         │
         ▼
AgentResponse(
    answer="Vineet has skills in Python, LangChain...",
    route_used="rag",
    sources=[{"filename": "skills.txt", "page": 1, ...}]
)
```

---

## Security Considerations

| Risk               | Mitigation                                                                            |
| ------------------ | ------------------------------------------------------------------------------------- |
| API key exposure   | Keys in `.env` only, never in `config.yaml` or code                                   |
| Prompt injection   | System prompt instructs agent to ignore override attempts; tested in `test_llm_io.py` |
| File upload abuse  | Extension whitelist (`SUPPORTED_EXTENSIONS`), filename sanitisation                   |
| CORS               | Configured to trusted origins only in production                                      |
| Non-root container | Docker runs as user `vineet` (UID 1000)                                               |
| Large file DoS     | Upload size limited by FastAPI / reverse proxy                                        |

---

## Technology Justification

| Decision        | Chosen                   | Rationale                                                       |
| --------------- | ------------------------ | --------------------------------------------------------------- |
| Agent framework | LangChain                | Mature, extensive tool ecosystem, excellent RAG support, LCEL   |
| LLM abstraction | LiteLLM                  | 100+ providers, unified API, zero code change to switch         |
| Vector store    | ChromaDB                 | Auto-persist, metadata filtering, simple setup vs Pinecone cost |
| Embeddings      | sentence-transformers    | Free, local, no API key, production-quality                     |
| Scheduler       | APScheduler              | Lightweight, no broker required (vs Celery Beat)                |
| File watcher    | watchdog                 | Cross-platform, battle-tested                                   |
| API layer       | FastAPI                  | Async, auto-docs, Pydantic validation, WebSocket support        |
| Config          | Pydantic Settings + YAML | Type-safe, env-override, readable                               |
| UI              | Streamlit                | Python-native, rapid iteration, easy custom CSS                 |
