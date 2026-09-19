# Security notes

LoopGrid MCP is intentionally a thin bridge. It does not directly access the LoopGrid database or signing keys and does not import LoopGrid core application code.

## Important defaults

- The target LoopGrid URL is operator-configured through `LOOPGRID_BASE_URL`; MCP tool arguments cannot redirect requests to another host.
- Caller-provided IDs used in URL paths are encoded as single path segments before requests are sent.
- `loopgrid.record_action` records execution evidence; it does **not** execute the business action.
- `loopgrid.record_outcome` records an outcome reported by the calling integration; it does not independently query or prove the downstream system state.
- Canonical fields such as action tool name, outcome status and `verified_against` cannot be overwritten through free-form `details`.
- MCP provenance metadata is fixed to `source=loopgrid-mcp` and cannot be overwritten by caller metadata.
- `loopgrid.record_review` is disabled by default because MCP tools are model-callable.
- Reviewer identity comes from `LOOPGRID_MCP_REVIEWER_ID`, not from a model-supplied tool argument.
- Evidence exports exclude raw FULL-mode disclosure payloads by default.
- Raw payload export requires `LOOPGRID_MCP_ALLOW_PAYLOAD_EXPORT=true`.
- Service API keys are sent only in the `X-LoopGrid-Key` request header and are never intentionally placed in evidence payloads or logs.
- Evidence downloads have a configurable maximum size and use a sanitized local filename.

## Evidence semantics

LoopGrid MCP captures evidence supplied by the integration. Cryptographic verification can show whether the captured LoopGrid record has been altered under the relevant signing/hash-chain rules. It does not, by itself, establish that every external statement supplied by a caller was truthful or that an external action actually occurred.

Integrations that need stronger external-action assurance should obtain authoritative receipts/results from the downstream system and record those references or results as evidence.

## Deployment guidance

For remote LoopGrid deployments:

- use HTTPS;
- use the minimum service-key scopes required by enabled tools;
- do not expose service keys in MCP arguments, prompts or source control;
- keep the human-review tool disabled unless the host workflow genuinely enforces human confirmation;
- keep raw payload export disabled unless disclosure export is explicitly intended.

## Reporting a security issue

Do not open a public GitHub issue containing secrets, credentials, private evidence bundles or exploit details. Use the private security-reporting mechanism configured on the GitHub repository once published.
