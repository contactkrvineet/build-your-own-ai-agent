"""Tests for document ingestion."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from app.rag.ingestion import (
    SUPPORTED_EXTENSIONS,
    _load_text,
    _load_markdown,
    load_documents,
)


class TestSupportedExtensions:
    def test_contains_expected_types(self):
        assert ".pdf" in SUPPORTED_EXTENSIONS
        assert ".txt" in SUPPORTED_EXTENSIONS
        assert ".docx" in SUPPORTED_EXTENSIONS
        assert ".md" in SUPPORTED_EXTENSIONS

    def test_does_not_contain_unsupported(self):
        assert ".exe" not in SUPPORTED_EXTENSIONS
        assert ".xlsx" not in SUPPORTED_EXTENSIONS


class TestTextLoader:
    def test_loads_plain_text(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("Vineet Kumar is an SDET Manager.", encoding="utf-8")
        docs = _load_text(f)
        assert len(docs) == 1
        assert "Vineet Kumar" in docs[0].page_content

    def test_metadata_includes_filename(self, tmp_path):
        f = tmp_path / "bio.txt"
        f.write_text("Some content", encoding="utf-8")
        docs = _load_text(f)
        assert docs[0].metadata["filename"] == "bio.txt"

    def test_empty_file_returns_empty_list(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        docs = _load_text(f)
        assert docs == []


class TestMarkdownLoader:
    def test_loads_markdown(self, tmp_path):
        f = tmp_path / "readme.md"
        f.write_text("# AskVineet\n\nAI agent built by Vineet Kumar.", encoding="utf-8")
        docs = _load_markdown(f)
        assert len(docs) == 1
        assert "AskVineet" in docs[0].page_content


class TestLoadDocuments:
    def test_loads_from_directory(self, tmp_documents_dir):
        docs = load_documents(folder_path=str(tmp_documents_dir))
        assert len(docs) >= 2  # sample.txt + skills.md

    def test_empty_directory_returns_empty(self, tmp_path):
        docs = load_documents(folder_path=str(tmp_path))
        assert docs == []

    def test_missing_directory_returns_empty(self, tmp_path):
        non_existent = str(tmp_path / "does_not_exist")
        docs = load_documents(folder_path=non_existent)
        assert docs == []
