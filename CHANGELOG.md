# Changelog

## 0.1.0 - design preview

- Separate MCP server repository; no LoopGrid core-code changes.
- Six namespaced MCP tools for decision-evidence capture/retrieval.
- REST-only integration boundary against LoopGrid v0.8.x API.
- Local stdio transport; no separate hosted MCP service required.
- Human-review tool disabled by default.
- Reviewer identity controlled by operator configuration.
- Raw disclosure export disabled by default.
- Evidence ZIP size cap and sanitized local output path.
- Canonical action/outcome/provenance fields protected from free-form overrides.
- Caller-provided path identifiers URL-encoded as single path segments.
- Doctor command, REST smoke test and official-MCP-client stdio E2E test.
- Cross-platform GitHub Actions test matrix plus package-build and repository-hygiene checks.
- MCP Registry draft metadata prepared for future PyPI + Registry publication.
