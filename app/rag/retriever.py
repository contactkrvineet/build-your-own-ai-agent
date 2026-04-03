"""
RAG retriever — builds the full retrieval-augmented generation chain.

Pipeline:
  User query → embed → vector store similarity search → top-K docs
             → stuff into prompt → LLM → grounded answer
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional, Tuple

from langchain.chains import RetrievalQA
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from app.config.settings import get_settings
from app.llm.factory import create_langchain_llm
from app.rag.chunker import chunk_documents
from app.rag.ingestion import load_documents
from app.rag.vectorstore import add_documents_to_store, get_or_create_vectorstore
from app.utils.logger import logger


# ---------------------------------------------------------------------------
# One-shot build helper
# ---------------------------------------------------------------------------

def build_rag_pipeline(force_reload: bool = False) -> Tuple[VectorStore, RetrievalQA]:
    """
    Ingest documents, build/load the vector store, and return:
      - The raw VectorStore (for incremental updates)
      - A ready-to-call RetrievalQA chain

    Args:
        force_reload: Re-ingest all documents even if the store exists.
    """
    s = get_settings()

    # 1. Load raw documents
    docs = load_documents()

    # 2. Chunk them
    chunks = chunk_documents(docs) if docs else []

    # 3. Build / update vector store
    store = get_or_create_vectorstore(chunks if (chunks or force_reload) else None)

    # 4. Create QA chain
    qa_chain = _create_qa_chain(store)

    logger.info("RAG pipeline ready.")
    return store, qa_chain


def retrieve_relevant_docs(
    query: str,
    store: VectorStore,
    top_k: Optional[int] = None,
) -> List[Document]:
    """Retrieve top-K most relevant document chunks for *query*."""
    s = get_settings()
    k = top_k or s.rag_top_k
    results = store.similarity_search(query, k=k)
    logger.debug(f"Retrieved {len(results)} docs for query: '{query[:60]}…'")
    return results


def add_new_document_to_store(
    file_path: str, store: VectorStore
) -> None:
    """
    Hot-reload: ingest a single newly-dropped file and add its chunks
    to the existing vector store without rebuilding the whole index.
    """
    from app.rag.ingestion import load_single_document

    docs = load_single_document(file_path)
    if not docs:
        logger.warning(f"Nothing to index from {file_path}")
        return

    chunks = chunk_documents(docs)
    add_documents_to_store(store, chunks)
    logger.info(f"Hot-reloaded '{file_path}' — {len(chunks)} chunk(s) added")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _create_qa_chain(store: VectorStore) -> RetrievalQA:
    s = get_settings()
    llm = create_langchain_llm()
    retriever = store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": s.rag_top_k},
    )
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
    )
    return chain
