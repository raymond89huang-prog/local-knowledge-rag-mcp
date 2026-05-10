# Roadmap

Local Knowledge Reg MCP is a local knowledge registry MCP service for product managers and product teams. The first product goal is simple: connect local knowledge folders, keep them indexed, and let Codex, Claude Code, and CCC retrieve source-backed context while writing product documents.

## v0.1: Local Product Knowledge MCP

- Multiple local vaults in one config file.
- Supported document formats: `.md`, `.txt`, `.docx`, `.pdf`, `.csv`, `.xlsx`.
- Include and exclude glob rules per vault.
- Full indexing and incremental indexing.
- File watcher for create, update, and delete events.
- Correct index cleanup when a file changes or is deleted.
- MCP tools:
  - `search_docs`
  - `list_vaults`
  - `reindex`
- Search results include source references:
  - `.md` / `.txt`: heading or section
  - `.docx`: heading or paragraph section
  - `.pdf`: page
  - `.csv` / `.xlsx`: sheet and row range
- `doctor` command for local setup diagnostics.

## v0.2: Writing Experience

- Better result deduplication.
- Merge adjacent chunks from the same source.
- Better chunking for long sections and tables.
- Filters by vault, file type, path, and update time.
- `get_doc_context` MCP tool for wider source context.
- Cleaner citation formats for PRD, weekly report, proposal, and retrospective writing.

## v0.3: Retrieval Quality

- Hybrid Search: semantic search plus keyword search.
- Business glossary and synonym configuration.
- Better exact matching for module names, metric names, PRD IDs, and version names.
- Basic reranking.
- Chinese tokenization improvements.
- Tunable search parameters such as `semantic_weight`, `keyword_weight`, `top_k`, and `min_score`.

## v0.4: Open Source Readiness

- PyPI release.
- CI checks.
- Unit and integration tests.
- Product-team configuration templates.
- Example knowledge vault.
- Complete README, CHANGELOG, CONTRIBUTING, LICENSE, and privacy notes.
