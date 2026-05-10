from doc_rag.loaders import LoaderRegistry
from doc_rag.loaders.markdown import MarkdownLoader
from doc_rag.loaders.spreadsheet import SpreadsheetLoader
from doc_rag.loaders.text import TextLoader


def test_loader_registry_lists_v01_formats():
    assert LoaderRegistry().supported_extensions() == {
        ".csv",
        ".docx",
        ".markdown",
        ".md",
        ".pdf",
        ".txt",
        ".xlsx",
    }


def test_markdown_loader_preserves_title_tags_heading_and_wiki_links(tmp_path):
    path = tmp_path / "prd.md"
    path.write_text(
        """---
title: Member PRD
tags:
  - prd
---

# Background
This section mentions [[Member Center|member center]] and retention policy.
""",
        encoding="utf-8",
    )

    chunks = MarkdownLoader().load(path)

    assert len(chunks) == 1
    assert chunks[0].title == "Member PRD"
    assert chunks[0].heading == "Background"
    assert chunks[0].tags == ["prd"]
    assert chunks[0].metadata["wiki_links"] == ["Member Center"]
    assert chunks[0].metadata["file_type"] == "md"


def test_text_loader_returns_single_document_chunk(tmp_path):
    path = tmp_path / "meeting.txt"
    path.write_text("Meeting notes about payment success rate and risk controls.", encoding="utf-8")

    chunks = TextLoader().load(path)

    assert len(chunks) == 1
    assert chunks[0].title == "meeting"
    assert chunks[0].metadata["file_type"] == "txt"


def test_csv_loader_records_sheet_row_location(tmp_path):
    path = tmp_path / "metrics.csv"
    path.write_text("metric,definition\nDAU,Daily active users\nGMV,Gross merchandise value\n", encoding="utf-8")

    chunks = SpreadsheetLoader().load(path)

    assert len(chunks) == 1
    assert chunks[0].metadata["file_type"] == "csv"
    assert chunks[0].metadata["sheet"] == "metrics"
    assert chunks[0].metadata["row_start"] == 2
    assert chunks[0].metadata["row_end"] == 3
    assert "DAU" in chunks[0].content

