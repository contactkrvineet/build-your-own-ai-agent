"""
Embedding model management.
Uses sentence-transformers (local, no API key required) by default.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_community.embeddings import HuggingFaceEmbeddings

from app.config.settings import get_settings
from app.utils.logger import logger


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Return a cached HuggingFace sentence-transformers embedding model.

    The model is downloaded on first call and cached locally by
    sentence-transformers in ~/.cache/huggingface/.

    Config key: rag.embedding_model
    Recommended models:
      - all-MiniLM-L6-v2   (small, fast — good default)
      - all-mpnet-base-v2  (larger, better quality)
      - BAAI/bge-small-en-v1.5 (excellent quality/speed trade-off)
    """
    s = get_settings()
    model_name = s.rag_embedding_model

    logger.info(f"Loading embedding model: {model_name}")

    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    logger.info(f"Embedding model loaded: {model_name}")
    return embeddings
