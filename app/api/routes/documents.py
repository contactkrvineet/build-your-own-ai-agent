"""
Document management routes.

POST /documents/upload   — upload a file and index it immediately
GET  /documents/list     — list ingested documents
POST /documents/reload   — re-index all documents from the configured folder
"""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app.config.settings import get_settings
from app.rag.ingestion import SUPPORTED_EXTENSIONS
from app.utils.logger import logger

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", summary="Upload a document and index it immediately")
async def upload_document(file: UploadFile) -> dict:
    s = get_settings()
    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{suffix}'. "
                f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
            ),
        )

    # Sanitise filename
    safe_name = Path(file.filename).name
    dest = Path(s.rag_documents_path) / safe_name
    dest.parent.mkdir(parents=True, exist_ok=True)

    with dest.open("wb") as f_out:
        content = await file.read()
        f_out.write(content)

    logger.info(f"Document uploaded: {dest}")

    # Tell file watcher to skip this file (upload route handles indexing)
    try:
        from app.workflows.file_watcher import skip_file_watcher
        skip_file_watcher(str(dest))
    except Exception:
        pass

    # Trigger hot-reload via agent
    try:
        from app.agent.core import get_agent

        agent = get_agent()
        agent.add_document(str(dest))
        indexed = True
    except Exception as e:
        logger.error(f"Indexing failed for {dest}: {e}")
        indexed = False

    return {
        "filename": safe_name,
        "size_bytes": len(content),
        "indexed": indexed,
        "path": str(dest),
    }


@router.get("/list", summary="List documents in the configured documents folder")
async def list_documents() -> dict:
    s = get_settings()
    docs_path = Path(s.rag_documents_path)

    if not docs_path.exists():
        return {"documents": [], "total": 0}

    docs = [
        {
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "extension": f.suffix.lower(),
        }
        for f in docs_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    return {"documents": docs, "total": len(docs), "folder": str(docs_path.resolve())}


@router.post("/reload", summary="Re-ingest all documents from the documents folder")
async def reload_documents() -> dict:
    try:
        from app.agent.core import get_agent

        agent = get_agent()
        agent.reload_documents()
        return {"status": "ok", "message": "Documents reloaded and re-indexed."}
    except Exception as e:
        logger.error(f"Reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
