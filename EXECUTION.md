# AskVineet — Complete Execution Guide

> Copy-paste every command block in order. Nothing is skipped.

---

## 0. Prerequisites

| Requirement              | Minimum version | Check                                        |
| ------------------------ | --------------- | -------------------------------------------- |
| Python                   | 3.11            | `python3 --version`                          |
| pip                      | 23+             | `pip3 --version`                             |
| Git                      | any             | `git --version`                              |
| Docker + Compose         | 24 + 2.20       | `docker --version && docker compose version` |
| Tesseract OCR (optional) | 4+              | `tesseract --version`                        |

**macOS Tesseract install (optional — only needed for scanned PDFs):**

```bash
brew install tesseract poppler
```

**Ubuntu/Debian Tesseract install (optional — Linux servers only, skip on macOS):**

```bash
sudo apt-get update && sudo apt-get install -y tesseract-ocr poppler-utils
```

> **Note:** On macOS use `brew install tesseract poppler` (shown above). The `apt-get` command is for Linux only (e.g. your remote deploy server).

---

## 1. Clone & Enter Project

```bash
# If you haven't already initialised the repo
cd /Users/vineetkumar/Documents/STUDY/AgentVineet

# Verify you are in the right directory
ls config.yaml requirements.txt Dockerfile
```

---

## 2. Create & Activate Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows
python --version                   # should say 3.11.x
```

---

## 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs ~40 packages including LangChain, LiteLLM, ChromaDB, FastAPI, Streamlit, sentence-transformers, and all test tools.

---

## 4. Configure Secrets

```bash
cp .env.example .env
```

Open `.env` and fill in **at least one** LLM provider key:

```bash
# Fastest free option — get key at https://console.groq.com/
GROQ_API_KEY=gsk_XXXXXXXXXXXXXXXXXXXX

# Match the provider in config.yaml (see Step 5)
LLM_PROVIDER=groq
LLM_MODEL=llama3-8b-8192
```

Other optional keys (leave blank to disable those features):

```
OPENAI_API_KEY=           # OpenAI
ANTHROPIC_API_KEY=        # Claude
GOOGLE_API_KEY=           # Gemini
OPENWEATHERMAP_API_KEY=   # Weather tool
```

---

## 5. Review Main Config (Optional)

```bash
cat config.yaml
```

Key settings to know:

```yaml
llm:
  provider: groq # change to openai | anthropic | gemini | ollama | huggingface
  model: llama3-8b-8192 # provider-specific model name

rag:
  vector_store: chroma # or faiss
  hot_reload: true # auto-index new files dropped in documents/

tools:
  weather:
    enabled: false # set true + add OPENWEATHERMAP_API_KEY to .env
```

No code changes needed — config.yaml + .env drive everything.

---

## 6. Add Your Documents (Optional but Recommended)

```bash
# Drop any PDF, TXT, DOCX, or Markdown files here
cp ~/Downloads/vineet_resume.pdf documents/
cp ~/Downloads/vineet_skills.txt documents/
ls documents/
```

The agent will answer questions about these files via RAG.

---

## 7. Run the FastAPI Backend

```bash
# In terminal 1 — leave this running
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Expected output:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     AskVineet Agent initialised successfully
INFO:     Scheduler started
INFO:     File watcher started on ./documents
```

Verify the API is up:

```bash
curl http://localhost:8000/health/
# {"status":"healthy","agent":"AskVineet","version":"1.0.0",...}
```

---

## 8. Run the Streamlit Chat UI

```bash
# In terminal 2 (new tab)
source .venv/bin/activate
streamlit run ui/streamlit_app.py --server.port 8501
```

Open: **http://localhost:8501**

You should see the black terminal UI with green text. Type a message and hit Enter.

---

## 9. Send a Chat Request via API (Optional)

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, who are you?", "session_id": "test-001"}'
```

```bash
# RAG query
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "What are Vineetas skills?", "session_id": "test-001"}'
```

```bash
# Upload a document
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@documents/vineet_test.pdf"
```

---

## 10. Run the Test Suite

```bash
# In terminal 3 (new tab)
source .venv/bin/activate

# All unit tests (no LLM calls, fully mocked)
pytest tests/ -v -m "not live"

# Just the LLM I/O validation showcase
pytest tests/test_validation/ -v

# Run with coverage report
pytest tests/ -m "not live" --cov=app --cov-report=term-missing

# Live integration tests (require a real LLM key in .env)
pytest tests/ -m live -v
```

Expected output (all unit tests):

```
tests/test_agent/test_core.py         PASSED
tests/test_agent/test_router.py       PASSED
tests/test_llm/test_providers.py      PASSED
tests/test_rag/test_ingestion.py      PASSED
tests/test_rag/test_retriever.py      PASSED
tests/test_tools/test_tools.py        PASSED
tests/test_api/test_chat.py           PASSED
tests/test_validation/test_llm_io.py  PASSED

42 passed in ~8s
```

---

## 11. Run via Docker (Production-Like)

```bash
# Build images
docker compose build

# Start all services (API on :8000, UI on :8501)
docker compose up -d

# Check logs
docker compose logs -f api
docker compose logs -f ui

# Stop
docker compose down
```

> Docker reads `.env` automatically. No extra config needed.

Open:

- API: http://localhost:8000/docs (Swagger UI)
- Chat UI: http://localhost:8501

---

## 12. Execute a YAML Workflow Manually

```bash
# Trigger the sample workflow via REST
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Run the sample workflow", "session_id": "workflow-test"}'

# Or use Python directly
python - <<'EOF'
import asyncio
from app.workflows.pipeline import load_pipeline_from_file

async def main():
    pipeline = load_pipeline_from_file("workflows/sample_workflow.yaml")
    result = await pipeline.run()
    print(result)

asyncio.run(main())
EOF
```

---

## 13. Explore the API Docs

With the FastAPI server running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 14. Switch LLM Provider (Zero Code Change)

```bash
# Edit .env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-XXXXXXXX

# Or edit config.yaml
# llm:
#   provider: anthropic
#   model: claude-3-5-sonnet-20241022

# Restart the API
# CTRL+C in terminal 1, then:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

No Python files change. That's the point.

---

## 15. Use Ollama (Fully Local, No API Key)

```bash
# Install Ollama: https://ollama.com
brew install ollama           # macOS
ollama serve &                # Start Ollama daemon
ollama pull llama3            # Download model (~4 GB)

# Edit .env
LLM_PROVIDER=ollama
LLM_MODEL=llama3

# Restart API — now 100% local, zero cloud calls
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Quick Reference

| Action       | Command                                                         |
| ------------ | --------------------------------------------------------------- |
| Start API    | `uvicorn app.main:app --reload --port 8000`                     |
| Start UI     | `streamlit run ui/streamlit_app.py --server.port 8501`          |
| Run tests    | `pytest tests/ -v -m "not live"`                                |
| Docker up    | `docker compose up -d`                                          |
| Docker down  | `docker compose down`                                           |
| Upload doc   | `curl -X POST .../documents/upload -F "file=@path/to/file.pdf"` |
| Health check | `curl http://localhost:8000/health/`                            |
| API docs     | http://localhost:8000/docs                                      |

---

## Troubleshooting

**`ModuleNotFoundError`** — virtual environment not activated:

```bash
source .venv/bin/activate
```

**`litellm.exceptions.AuthenticationError`** — wrong or missing API key:

```bash
cat .env | grep API_KEY    # check keys are present
```

**ChromaDB `sqlite3` error on Python 3.11+** — install pysqlite3:

```bash
pip install pysqlite3-binary
# Then add to app/__init__.py:
# import sys; __import__('pysqlite3'); sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
```

**Streamlit can't reach API** — ensure FastAPI is running on port 8000 first.

**Docker build fails on Apple Silicon** — add platform flag:

```bash
docker compose build --build-arg BUILDPLATFORM=linux/amd64
```

**Tesseract not found** — OCR is optional; disable with `rag.ocr_enabled: false` in `config.yaml`.

---

## 16. Production Deployment via GitHub Actions

A CI/CD pipeline is defined at `.github/workflows/deploy.yml`. It runs three jobs on every push to `main`:

| Job        | What it does                                                                             |
| ---------- | ---------------------------------------------------------------------------------------- |
| **test**   | Installs deps, runs `pytest tests/ -m "not live"`                                        |
| **build**  | Builds the Docker image and pushes to `ghcr.io`                                          |
| **deploy** | SSHs into the remote server, pulls the image, writes `.env`, runs `docker compose up -d` |

### 16.1 GitHub Secrets (Settings → Secrets → Actions)

These are **required**:

| Secret           | Description                                      |
| ---------------- | ------------------------------------------------ |
| `GROQ_API_KEY`   | Groq API key (or whichever LLM provider you use) |
| `SECRET_KEY`     | Application secret (random 32+ char string)      |
| `DEPLOY_HOST`    | Remote server IP or hostname                     |
| `DEPLOY_USER`    | SSH username on the remote server                |
| `DEPLOY_SSH_KEY` | Private SSH key (ed25519 recommended)            |

These are **optional** (only add if you use the feature):

| Secret                   | Feature                   |
| ------------------------ | ------------------------- |
| `OPENAI_API_KEY`         | OpenAI provider           |
| `ANTHROPIC_API_KEY`      | Anthropic/Claude provider |
| `GOOGLE_API_KEY`         | Gemini provider           |
| `HUGGINGFACE_API_TOKEN`  | HuggingFace provider      |
| `OPENWEATHERMAP_API_KEY` | Weather tool              |
| `CUSTOM_API_KEY`         | Custom REST API tool      |
| `LANGCHAIN_API_KEY`      | LangSmith observability   |

### 16.2 GitHub Variables (Settings → Variables → Actions)

Non-secret configuration — these fall through to `.env` on the server:

| Variable               | Default          | Description              |
| ---------------------- | ---------------- | ------------------------ |
| `APP_ENV`              | `production`     | Application environment  |
| `LLM_PROVIDER`         | `groq`           | LLM provider name        |
| `LLM_MODEL`            | `llama3-8b-8192` | Model identifier         |
| `LANGCHAIN_TRACING_V2` | `false`          | Enable LangSmith tracing |
| `LANGCHAIN_PROJECT`    | `askvineet`      | LangSmith project name   |
| `LITELLM_LOG`          | `ERROR`          | LiteLLM log verbosity    |

### 16.3 Remote Server Prerequisites

The deploy target must have:

```bash
# Docker + Compose
docker --version        # 24+
docker compose version  # 2.20+

# Git
git --version
```

### 16.4 Trigger a Deploy

```bash
# Automatic: push to main
git push origin main

# Manual: GitHub → Actions → "CI/CD — Test, Build, Deploy" → Run workflow
```

### 16.5 Verify Production

```bash
# From your local machine (replace with your server IP)
curl https://your-server.com/health/
curl https://your-server.com/health/llm

# SSH into server and check logs
ssh user@your-server.com
cd ~/askvineet
docker compose logs -f api
docker compose logs -f ui
```

---

## 17. Running All Servers — Quick Reference

### Local Development (no Docker)

```bash
# Terminal 1 — FastAPI backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Streamlit UI
source .venv/bin/activate
streamlit run ui/streamlit_app.py --server.port 8501
```

### Local with Docker

```bash
# Start both services
docker compose up --build -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Production (remote server via CI/CD)

Push to `main` → GitHub Actions builds, pushes, and deploys automatically.

```bash
# Manual deploy (on the server itself)
cd ~/askvineet
git pull origin main
docker compose pull
docker compose up -d --remove-orphans
```

| Service         | Local URL                     | Production URL                  |
| --------------- | ----------------------------- | ------------------------------- |
| FastAPI Backend | http://localhost:8000         | https://your-domain.com         |
| Swagger Docs    | http://localhost:8000/docs    | https://your-domain.com/docs    |
| Health Check    | http://localhost:8000/health/ | https://your-domain.com/health/ |
| Streamlit UI    | http://localhost:8501         | https://your-domain.com:8501    |
