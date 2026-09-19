# LoopGrid MCP Server — v0.1 design preview

**A thin Model Context Protocol bridge for the LoopGrid evidence plane.**

<!-- mcp-name: io.github.loopgridio/loopgrid-mcp -->

`loopgrid-mcp` lets an MCP-compatible host record and retrieve LoopGrid decision evidence through six MCP tools. It is intentionally a **separate repository** from the LoopGrid core product and talks to LoopGrid only through its REST API.

It does not import LoopGrid internals, access the LoopGrid database directly, change signing code, alter the evidence schema, or modify the existing LoopGrid SDK contracts.

## Architecture

```text
MCP-compatible AI host/client
          |
          | stdio MCP
          v
     loopgrid-mcp
          |
          | LoopGrid REST API
          v
        LoopGrid
          |
          v
 signed, tamper-evident decision evidence
```

The v0.1 release uses **local stdio**. No separate Railway, Render, AWS, database, or hosted MCP service is required.

## MCP tools

The server exposes:

- `loopgrid.record_decision`
- `loopgrid.record_review`
- `loopgrid.record_action`
- `loopgrid.record_outcome`
- `loopgrid.get_evidence`
- `loopgrid.verify_evidence`

## Important safety boundary

LoopGrid MCP is an **evidence bridge**, not a business-action executor.

`loopgrid.record_action` does not issue a Stripe refund, edit Salesforce, change ServiceNow, or invoke another business system. It records evidence supplied by the calling integration that an external action occurred.

Likewise, `loopgrid.record_outcome` records an outcome reported by the integration. LoopGrid can verify the integrity of the captured record; this alone does not independently prove that every external-world claim is true or establish legal compliance.

Human review receives extra protection: `loopgrid.record_review` is registered but **disabled by default**. To enable it, an operator must explicitly set the review flag and reviewer identity. The model cannot choose the configured reviewer identity.

Raw FULL-mode disclosures are also excluded from MCP evidence export by default.

## Requirements

- Python 3.10+
- A reachable LoopGrid v0.8.x service
- For local evaluation, the public LoopGrid GHCR image is sufficient

Normal use of this Python stdio server does **not** require Node.js. Node is only needed for optional browser-based MCP Inspector tooling.

The project uses the official MCP Python SDK v2 line (`mcp>=2,<3`).

## Windows quick start

### 1. Start LoopGrid

In PowerShell:

```powershell
docker run --rm `
  --platform linux/amd64 `
  -p 8000:8000 `
  -v loopgrid_demo_data:/app/data `
  ghcr.io/cybertechsoft/loopgrid:edge
```

Leave that container running.

### 2. Prepare this repository

Open another PowerShell window in the `loopgrid-mcp` folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 3. Check connectivity

```powershell
loopgrid-mcp-doctor
```

Expected shape:

```text
[OK] LoopGrid reachable: http://127.0.0.1:8000
[OK] version: 0.8.1-design-partner
[OK] evidence profile: 3.0-draft
[OK] database: ok
[OK] signer: local_ed25519
[OK] MCP workspace: default
```

### 4. Run the unit/protocol tests

```powershell
python -m pytest -ra
```

### 5. Run a real REST smoke test

```powershell
python .\scripts\smoke_test.py
```

This creates a synthetic decision, records synthetic action/outcome evidence, verifies the decision, and downloads an evidence ZIP. It does not call a real external business system.

### 6. Run the real stdio MCP client test

```powershell
python .\scripts\mcp_stdio_test.py
```

This launches `loopgrid-mcp` as a child stdio server using the official MCP Python client and verifies:

```text
connect
  -> discover all 6 tools
  -> record decision
  -> record action evidence
  -> record outcome evidence
  -> service-side verification
  -> evidence ZIP export
  -> review tool remains disabled by default
```

A successful run ends with:

```text
[PASS] Real stdio MCP client test completed successfully.
```

This is the recommended release-gate test for the MCP protocol path.

## Start the MCP server

```powershell
loopgrid-mcp
```

A real MCP host normally starts this command for you. Because this is a stdio server, running it directly simply waits for MCP messages on standard input.

A generic MCP client configuration is:

```json
{
  "mcpServers": {
    "loopgrid": {
      "command": "loopgrid-mcp",
      "env": {
        "LOOPGRID_BASE_URL": "http://127.0.0.1:8000",
        "LOOPGRID_WORKSPACE": "default"
      }
    }
  }
}
```

On Windows, some hosts need the full path to `.venv\\Scripts\\loopgrid-mcp.exe`. See `examples/mcp-client-config.windows.json`.

## Optional MCP Inspector

The browser Inspector is useful for manual exploration, but it is not required to run or validate LoopGrid MCP. The canonical automated protocol test in this repository is:

```powershell
python .\scripts\mcp_stdio_test.py
```

If your installed MCP development tooling supports the Inspector cleanly, you can also try:

```powershell
mcp dev .\src\loopgrid_mcp\server.py
```

## Tool behavior

### `loopgrid.record_decision`

Captures a decision through LoopGrid's REST API. It may also append model evidence and evaluate an existing LoopGrid policy when those optional inputs are supplied.

It never executes `proposed_action`.

Example:

```json
{
  "decision_type": "customer_refund",
  "agent_id": "support-agent",
  "agent_version": "1.0",
  "proposed_action": {
    "tool": "stripe.refunds.create",
    "amount": 720,
    "currency": "USD"
  },
  "model": {
    "provider": "openai",
    "name": "gpt-5"
  },
  "authority": {
    "acting_for": "Acme",
    "limit_usd": 1500,
    "scope": ["refund:create"]
  }
}
```

### `loopgrid.record_review`

Records an approve/reject review using the LoopGrid review endpoint. **Disabled by default.**

To enable deliberately:

```powershell
$env:LOOPGRID_MCP_ENABLE_REVIEW_TOOL="true"
$env:LOOPGRID_MCP_REVIEWER_ID="reviewer@example.com"
```

When LoopGrid authentication is enabled, the service key also needs the appropriate review scope.

### `loopgrid.record_action`

Appends `tool_executed` evidence. It does not execute the external tool. Canonical fields such as the tool name cannot be overwritten by free-form `details`.

### `loopgrid.record_outcome`

Appends `outcome_observed` evidence. The calling integration is responsible for obtaining the real downstream outcome. Canonical `status` and `verified_against` fields cannot be overwritten by free-form `details`.

### `loopgrid.get_evidence`

Downloads the portable evidence ZIP to `LOOPGRID_EVIDENCE_DIR` (default `./loopgrid-evidence`).

Raw disclosure payloads are blocked unless explicitly enabled:

```powershell
$env:LOOPGRID_MCP_ALLOW_PAYLOAD_EXPORT="true"
```

### `loopgrid.verify_evidence`

Asks the connected LoopGrid service to verify the decision's signed workspace chain. This is **service-side verification**.

For independent/offline verification of an exported ZIP, use the standalone LoopGrid verifier. The MCP bridge intentionally does not duplicate that verifier.

## Authenticated LoopGrid deployments

For local evaluation with authentication disabled, no service key is required.

When authentication is enabled:

```powershell
$env:LOOPGRID_SERVICE_KEY="<scoped-service-key>"
```

Use the minimum scopes required by the tools you enable. Do not use an admin key unless administration is genuinely required.

## Configuration

See `.env.example` for the full list of supported environment variables.

The bridge does **not** automatically load `.env`; the MCP host should inject variables, or the operator should set them in the environment that starts the server.

The target LoopGrid URL is operator configuration, not an MCP tool argument, so a model cannot redirect the bridge to an arbitrary host through a tool call.

## Repository boundary

The intended public layout is:

```text
github.com/cybertechsoft/loopgrid
    core LoopGrid evidence infrastructure

github.com/loopgridio/loopgrid-mcp
    thin MCP protocol bridge
```

The bridge communicates with LoopGrid only over HTTP.

## Validation status

The v0.1 release candidate has been exercised locally on Windows against the public LoopGrid v0.8.1 design-partner container. The real official MCP Python client successfully negotiated MCP protocol `2026-07-28`, discovered all six tools, created a synthetic decision, recorded action/outcome evidence, verified the evidence service-side, exported the evidence ZIP, and confirmed the review tool remained disabled by default.

See `VALIDATION.md` for the detailed release-gate record.

## MCP Registry preparation

The MCP Registry is **not published yet**.

`registry/server.json.draft` is preparation only. Publish order should be:

1. publish this GitHub repository;
2. obtain green CI from a clean checkout;
3. publish `loopgrid-mcp` to PyPI;
4. confirm the PyPI README contains the matching `mcp-name` marker;
5. validate/update `server.json` against the current Registry schema;
6. publish to the official MCP Registry.

The current MCP Registry supports PyPI package entries using stdio transport, and verifies PyPI ownership using the `mcp-name:` marker in the package README.

## Release posture

`0.1.0` is a **design preview**, not Production GA. It is intended to validate a clean MCP integration path for LoopGrid v0.8.x without changing LoopGrid's signing, hash-chain, evidence-bundle, verifier, or SDK contracts.

## License

Apache-2.0. See `LICENSE`.
