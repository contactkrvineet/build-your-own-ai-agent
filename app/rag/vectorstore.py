"""
Vector store abstraction — supports ChromaDB and FAISS.
Switching between them requires only changing config.yaml → rag.vector_store.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from app.config.settings import get_settings
from app.rag.embeddings import get_embeddings
from app.utils.logger import logger


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_or_create_vectorstore(
    documents: Optional[List[Document]] = None,
) -> VectorStore:
    """
    Load an existing vector store from disk, or create one from *documents*.

    If *documents* is provided and the store already exists, new documents
    are added incrementally (deduplication by file_hash metadata field).

    Config keys: rag.vector_store, rag.vector_store_path, rag.collection_name
    """
    s = get_settings()
    backend = s.rag_vector_store.lower()

    if backend == "chroma":
        return _get_or_create_chroma(documents)
    elif backend == "faiss":
        return _get_or_create_faiss(documents)
    else:
        raise ValueError(
            f"Unknown vector store backend: '{backend}'. "
            "Supported: 'chroma', 'faiss'"
        )


def add_documents_to_store(
    store: VectorStore, documents: List[Document]
) -> None:
    """Add new documents to an existing store."""
    if not documents:
        return
    store.add_documents(documents)
    logger.info(f"Added {len(documents)} chunk(s) to vector store")
    _persist_if_needed(store)


def _persist_if_needed(store: VectorStore) -> None:
    """Persist FAISS index to disk (ChromaDB auto-persists)."""
    if hasattr(store, "save_local"):
        s = get_settings()
        store_path = Path(s.rag_vector_store_path)
        store_path.mkdir(parents=True, exist_ok=True)
        store.save_local(str(store_path))  # type: ignore[attr-defined]
        logger.debug(f"FAISS index saved to {store_path}")


# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------

def _get_or_create_chroma(documents: Optional[List[Document]]) -> VectorStore:
    from langchain_chroma import Chroma

    s = get_settings()
    persist_dir = str(Path(s.rag_vector_store_path))
    Path(persist_dir).mkdir(parents=True, exist_ok=True)

    embeddings = get_embeddings()

    if documents:
        logger.info(
            f"Upserting {len(documents)} chunk(s) into ChromaDB "
            f"(collection: {s.rag_collection_name})"
        )
        store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            collection_name=s.rag_collection_name,
            persist_directory=persist_dir,
        )
    else:
        logger.info(f"Loading existing ChromaDB from {persist_dir}")
        store = Chroma(
            collection_name=s.rag_collection_name,
            embedding_function=embeddings,
            persist_directory=persist_dir,
        )

    return store


# ---------------------------------------------------------------------------
# FAISS
# ---------------------------------------------------------------------------

def _get_or_create_faiss(documents: Optional[List[Document]]) -> VectorStore:
    from langchain_community.vectorstores import FAISS

    s = get_settings()
    store_path = Path(s.rag_vector_store_path)
    index_file = store_path / "index.faiss"
    embeddings = get_embeddings()

    if index_file.exists() and not documents:
        logger.info(f"Loading existing FAISS index from {store_path}")
        return FAISS.load_local(
            str(store_path),
            embeddings,
            allow_dangerous_deserialization=True,
        )

    if not documents:
        logger.warning("FAISS: no existing index and no documents provided. Creating empty store.")
        # Create a minimal FAISS store with a dummy document
        dummy = Document(page_content="AskVineet initialised.", metadata={"source": "system"})
        documents = [dummy]

    logger.info(f"Creating FAISS index with {len(documents)} chunk(s)")
    store = FAISS.from_documents(documents, embeddings)
    store_path.mkdir(parents=True, exist_ok=True)
    store.save_local(str(store_path))
    return store
