"""Tests for RAG chunker and retriever components."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.rag.chunker import chunk_documents


class TestChunker:
    def test_returns_chunks(self, sample_documents):
        chunks = chunk_documents(sample_documents, chunk_size=100, chunk_overlap=20)
        assert len(chunks) >= len(sample_documents)

    def test_chunk_size_respected(self, sample_documents):
        chunks = chunk_documents(sample_documents, chunk_size=50, chunk_overlap=10)
        for chunk in chunks:
            assert len(chunk.page_content) <= 100  # Some tolerance for splitter

    def test_metadata_preserved(self, sample_documents):
        chunks = chunk_documents(sample_documents, chunk_size=500, chunk_overlap=50)
        for chunk in chunks:
            assert "source" in chunk.metadata
            assert "chunk_index" in chunk.metadata

    def test_empty_input_returns_empty(self):
        result = chunk_documents([])
        assert result == []

    def test_chunk_index_is_sequential(self, sample_documents):
        chunks = chunk_documents(sample_documents, chunk_size=200, chunk_overlap=20)
        indices = [c.metadata["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))


class TestRetriever:
    @patch("app.rag.retriever.create_langchain_llm")
    @patch("app.rag.retriever.get_or_create_vectorstore")
    @patch("app.rag.retriever.load_documents", return_value=[])
    def test_retrieve_relevant_docs(
        self, mock_load, mock_store_factory, mock_llm, mock_vector_store
    ):
        from app.rag.retriever import retrieve_relevant_docs

        mock_store_factory.return_value = mock_vector_store
        docs = retrieve_relevant_docs("Vineet skills", store=mock_vector_store, top_k=3)

        mock_vector_store.similarity_search.assert_called_once_with("Vineet skills", k=3)
        assert len(docs) == 1  # from the mock fixture
        assert "SDET Manager" in docs[0].page_content
