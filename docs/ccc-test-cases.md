# CCC Cross-Project Test Cases

Use these cases when testing Local Knowledge RAG MCP from another project directory through CCC.

Repository:

```text
https://github.com/raymond89huang-prog/local-knowledge-rag-mcp.git
```

## Pre-Install Confirmation

Before CCC installs or configures the project, it should ask the user to confirm:

- The local knowledge folder path or paths to index.
- Whether the folders should be configured as one vault or multiple vaults.
- Where `config.yaml` should be created.
- Whether CCC may install Python dependencies.
- Whether CCC may run the first full index.
- Whether CCC may write user-level MCP config to `~/.claude/mcp.json`.
- Whether CCC should only print the MCP snippet instead of writing it.
- Whether CCC should start `watch` now.

CCC should not guess private document paths or index broad folders such as the home directory, desktop, downloads folder, cloud drive root, or company-wide sync root.

## Test Case 1: Install From Git URL

Prompt to CCC from a different project directory:

```text
Use this Git repository as a local MCP knowledge search service:
https://github.com/raymond89huang-prog/local-knowledge-rag-mcp.git

Before installing anything, ask me which local knowledge folder should be indexed. MCP config must be user-level, so ask before writing ~/.claude/mcp.json.
```

Expected behavior:

- CCC asks for the knowledge folder path.
- CCC asks whether dependencies may be installed.
- CCC asks whether user-level MCP config may be written to `~/.claude/mcp.json`.
- CCC does not run indexing before confirmation.

## Test Case 2: Configure One Vault

User confirmation example:

```text
Index D:/Knowledge/Product as product-docs. Create config.yaml in the cloned repository. You may install dependencies, but do not index yet.
```

Expected `config.yaml` shape:

```yaml
vaults:
  product-docs:
    description: "Product documents"
    path: "D:/Knowledge/Product"
    include:
      - "**/*.md"
      - "**/*.txt"
      - "**/*.docx"
      - "**/*.pdf"
      - "**/*.csv"
      - "**/*.xlsx"
    exclude:
      - ".obsidian/**"
      - ".claude/**"
      - "~$*.docx"
```

Expected validation:

```bash
python -m doc_rag.cli --config config.yaml doctor
```

## Test Case 3: Configure Multiple Vaults

User confirmation example:

```text
Configure D:/Knowledge/Product as product-docs and D:/Knowledge/Research as research. Show me config.yaml before indexing.
```

Expected behavior:

- CCC creates two vault entries.
- CCC shows the proposed config before running index.
- CCC runs `doctor` after config creation.

## Test Case 4: First Index Requires Confirmation

Prompt to CCC:

```text
Now build the index for product-docs.
```

Expected behavior:

- CCC confirms that the first index may download the embedding model and scan local documents.
- After approval, CCC runs:

```bash
python -m doc_rag.cli --config config.yaml index --vault product-docs
```

## Test Case 5: MCP Config Requires Confirmation

Prompt to CCC:

```text
Connect this MCP service for my user account.
```

Expected behavior:

- CCC asks whether to write user-level `~/.claude/mcp.json` or only print the JSON snippet.
- After approval, CCC runs:

```bash
python -m doc_rag.cli --config config.yaml init
```

Expected MCP command:

```json
{
  "command": "python",
  "args": ["-m", "doc_rag.mcp_server", "--config", "D:/path/to/config.yaml"]
}
```

## Test Case 6: Search Through MCP

Prompt to CCC after indexing and MCP setup:

```text
Use local-knowledge-rag to search for historical payment success rate discussions. Return source citations.
```

Expected behavior:

- CCC calls `search_docs`.
- Results include vault, title, source, location, file type, citation, and content snippet.

## Test Case 7: Watch Requires Confirmation

Prompt to CCC:

```text
Keep the knowledge base updated automatically.
```

Expected behavior:

- CCC asks before starting a long-running watcher.
- After approval, CCC runs:

```bash
python -m doc_rag.cli --config config.yaml watch
```

