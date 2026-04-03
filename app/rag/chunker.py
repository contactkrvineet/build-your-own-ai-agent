"""
Text chunker — splits LangChain Documents into smaller chunks
for optimal embedding and retrieval.
"""

from __future__ import annotations

from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config.settings import get_settings
from app.utils.logger import logger


def chunk_documents(
    documents: List[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> List[Document]:
    """
    Split documents into chunks suitable for embedding.

    Args:
        documents:     Raw Document list from ingestion.
        chunk_size:    Override config value.
        chunk_overlap: Override config value.

    Returns:
        List of chunked Documents with inherited metadata.
    """
    if not documents:
        return []

    s = get_settings()
    size = chunk_size or s.rag_chunk_size
    overlap = chunk_overlap or s.rag_chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        length_function=len,
        # Prefer splitting on natural boundaries
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
    )

    chunks = splitter.split_documents(documents)

    # Enrich metadata with chunk index
    for idx, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = idx
        chunk.metadata["chunk_size"] = size

    logger.info(
        f"Chunked {len(documents)} document(s) → {len(chunks)} chunks "
        f"(size={size}, overlap={overlap})"
    )
    return chunks
