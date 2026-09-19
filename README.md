# LoopGrid MCP Server — v0.1 design preview

**MCP access to the LoopGrid evidence plane for consequential AI and agent decisions.**

<!-- mcp-name: io.github.loopgridio/loopgrid-mcp -->

`loopgrid-mcp` is a thin Model Context Protocol (MCP) bridge for LoopGrid.

It lets an MCP-compatible AI host record and retrieve signed, tamper-evident decision evidence through six MCP tools while keeping the MCP layer separate from the LoopGrid core runtime.

The bridge communicates with LoopGrid exclusively through its REST API. It does not import LoopGrid internals, access the LoopGrid database directly, change signing logic, alter the evidence schema, or modify the existing LoopGrid SDK contracts.

## Public release

Current version:

```text
0.1.0
```

Available through:

- **PyPI:** `loopgrid-mcp`
- **GitHub:** `github.com/loopgridio/loopgrid-mcp`
- **MCP Registry:** `io.github.loopgridio/loopgrid-mcp`

The official MCP Registry entry is active and currently points to the PyPI `0.1.0` package using local `stdio` transport.

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
 signed, tamper-evident
 decision evidence
```

The v0.1 release uses **local stdio** transport.

No separate hosted MCP service, Railway deployment, Render deployment, AWS service, or MCP-specific database is required.

## MCP tools

The server exposes six tools:

- `loopgrid.record_decision`
- `loopgrid.record_review`
- `loopgrid.record_action`
- `loopgrid.record_outcome`
- `loopgrid.get_evidence`
- `loopgrid.verify_evidence`

## Important safety boundary

LoopGrid MCP is an **evidence bridge**, not a business-action executor.

`loopgrid.record_action` does not issue a Stripe refund, modify Salesforce, change ServiceNow, or invoke another external business system. It records evidence supplied by the calling integration that an external action occurred.

Likewise, `loopgrid.record_outcome` records an outcome reported by the calling integration.

LoopGrid can cryptographically verify the integrity of the captured record. That verification does not independently prove that every external-world claim in the record is true and does not determine legal or regulatory compliance.

Human review receives additional protection. `loopgrid.record_review` is registered as an MCP tool but is **disabled by default**. To enable it, an operator must explicitly configure both the review flag and reviewer identity. The model cannot choose the configured reviewer identity.

Raw FULL-mode disclosure payloads are also excluded from MCP evidence export by default.

## Requirements

- Python 3.10+
- A reachable LoopGrid v0.8.x service
- For local evaluation, the public LoopGrid GHCR image is sufficient

Normal use of the Python stdio server does **not** require Node.js.

Node.js is only needed for optional browser-based MCP Inspector tooling.

The project uses the official MCP Python SDK v2 line:

```text
mcp>=2,<3
```

## Quick start

### 1. Start LoopGrid

For local evaluation using Docker:

```powershell
docker run --rm `
  --platform linux/amd64 `
  -p 8000:8000 `
  -v loopgrid_demo_data:/app/data `
  ghcr.io/cybertechsoft/loopgrid:edge
```

Leave the LoopGrid container running.

By default, LoopGrid MCP expects the service at:

```text
http://127.0.0.1:8000
```

### 2. Install LoopGrid MCP from PyPI

Create a Python virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Install the published package:

```powershell
pip install loopgrid-mcp
```

### 3. Check connectivity

Run:

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

The local evaluation configuration does not require a service key when LoopGrid authentication is disabled.

### 4. Start the MCP server

Run:

```powershell
loopgrid-mcp
```

Because this is a stdio MCP server, running it directly normally causes it to wait for MCP messages on standard input.

In normal use, an MCP-compatible host starts this command for you.

## Generic MCP client configuration

A generic client configuration looks like:

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

On Windows, some MCP hosts may require the full path to the executable, for example:

```text
.venv\Scripts\loopgrid-mcp.exe
```

See:

```text
examples/mcp-client-config.windows.json
```

for an example.

## Install from source

For development or repository validation:

```powershell
git clone https://github.com/loopgridio/loopgrid-mcp.git
cd loopgrid-mcp

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Then verify connectivity:

```powershell
loopgrid-mcp-doctor
```

## Development and validation

### Unit and protocol tests

Run:

```powershell
python -m pytest -ra
```

### Repository release check

Run:

```powershell
python .\scripts\release_check.py
```

### REST smoke test

Run:

```powershell
python .\scripts\smoke_test.py
```

The smoke test creates a synthetic decision, records synthetic action and outcome evidence, verifies the decision, and downloads an evidence ZIP.

It does not call a real external business system.

### Real stdio MCP client test

Run:

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

This is the recommended automated release-gate test for the MCP protocol path.

## Optional MCP Inspector

The browser-based MCP Inspector can be useful for manual exploration, but it is not required to run or validate LoopGrid MCP.

The canonical automated protocol test in this repository remains:

```powershell
python .\scripts\mcp_stdio_test.py
```

If your installed MCP development tooling supports the Inspector cleanly, you can also try:

```powershell
mcp dev .\src\loopgrid_mcp\server.py
```

## Tool behavior

### `loopgrid.record_decision`

Captures a decision through the LoopGrid REST API.

Optional inputs can also append model evidence and evaluate an existing LoopGrid policy.

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

Records an approve/reject review through the LoopGrid review endpoint.

This tool is **disabled by default**.

To enable it deliberately:

```powershell
$env:LOOPGRID_MCP_ENABLE_REVIEW_TOOL="true"
$env:LOOPGRID_MCP_REVIEWER_ID="reviewer@example.com"
```

When LoopGrid authentication is enabled, the configured service key must also have the appropriate review scope.

### `loopgrid.record_action`

Appends `tool_executed` evidence to the decision record.

It does **not** execute the external tool.

Canonical fields such as the tool name cannot be overwritten by free-form `details`.

### `loopgrid.record_outcome`

Appends `outcome_observed` evidence.

The calling integration is responsible for obtaining the real downstream outcome.

Canonical fields such as `status` and `verified_against` cannot be overwritten by free-form `details`.

### `loopgrid.get_evidence`

Downloads the portable LoopGrid evidence ZIP to:

```text
LOOPGRID_EVIDENCE_DIR
```

The default directory is:

```text
./loopgrid-evidence
```

Raw disclosure payloads are blocked from MCP evidence export unless explicitly enabled:

```powershell
$env:LOOPGRID_MCP_ALLOW_PAYLOAD_EXPORT="true"
```

### `loopgrid.verify_evidence`

Asks the connected LoopGrid service to verify the decision's signed workspace chain.

This is **service-side verification**.

Independent/offline verification of an exported evidence bundle should use the corresponding LoopGrid evidence-verification workflow rather than duplicating that verifier inside the MCP bridge.

## Authenticated LoopGrid deployments

For local evaluation with LoopGrid authentication disabled, no service key is required.

When authentication is enabled:

```powershell
$env:LOOPGRID_SERVICE_KEY="<scoped-service-key>"
```

Use the minimum scopes required by the MCP tools you enable.

Do not use an administrative key unless administration is genuinely required.

## Configuration

See:

```text
.env.example
```

for the complete supported environment-variable configuration.

Common settings include:

```text
LOOPGRID_BASE_URL
LOOPGRID_WORKSPACE
LOOPGRID_SERVICE_KEY
LOOPGRID_EVIDENCE_DIR
LOOPGRID_MCP_TIMEOUT_SECONDS
LOOPGRID_MCP_ENABLE_REVIEW_TOOL
LOOPGRID_MCP_REVIEWER_ID
LOOPGRID_MCP_ALLOW_PAYLOAD_EXPORT
```

The bridge does **not** automatically load `.env`.

The MCP host should inject environment variables, or the operator should configure them in the environment that starts the server.

The LoopGrid service URL is operator configuration rather than an MCP tool argument. This prevents a model from redirecting the bridge to an arbitrary LoopGrid host through a tool call.

## Privacy and disclosure defaults

LoopGrid supports evidence workflows with different disclosure levels.

The MCP bridge follows conservative defaults:

- human review recording is disabled unless explicitly enabled;
- reviewer identity is operator-configured;
- raw FULL-mode payload export is disabled by default;
- authenticated deployments should use scoped service keys;
- external business actions are never executed by the MCP bridge itself.

## Repository boundary

LoopGrid core and LoopGrid MCP intentionally remain separate:

```text
github.com/cybertechsoft/loopgrid
    core LoopGrid evidence infrastructure

github.com/loopgridio/loopgrid-mcp
    MCP protocol bridge
```

The MCP bridge communicates with the LoopGrid core runtime only over HTTP.

## Validation status

LoopGrid MCP `0.1.0` has been validated on Windows against the public LoopGrid `0.8.1-design-partner` container.

Validation included:

- clean repository installation;
- Python unit/protocol tests;
- REST connectivity;
- synthetic decision creation;
- action evidence recording;
- outcome evidence recording;
- service-side cryptographic verification;
- portable evidence ZIP export;
- official MCP Python client stdio negotiation;
- discovery of all six MCP tools;
- confirmation that the review tool remains disabled by default.

The official MCP Python client successfully negotiated MCP protocol:

```text
2026-07-28
```

See `VALIDATION.md` for the detailed release-gate record.

## MCP Registry

LoopGrid MCP is published in the official MCP Registry as:

```text
io.github.loopgridio/loopgrid-mcp
```

Current Registry version:

```text
0.1.0
```

Registry metadata:

```text
Status: active
Latest: true
Package registry: PyPI
Package: loopgrid-mcp
Transport: stdio
```

The Registry entry is publicly discoverable and points to:

```text
https://github.com/loopgridio/loopgrid-mcp
```

The corresponding Python package is published as:

```text
loopgrid-mcp==0.1.0
```

The hidden ownership marker near the top of this README:

```html
<!-- mcp-name: io.github.loopgridio/loopgrid-mcp -->
```

is intentionally retained because it is used for MCP Registry package ownership verification.

For future releases:

1. update the package version;
2. update `server.json` to the same version;
3. run the repository validation suite;
4. publish the new version to PyPI;
5. confirm the package is publicly installable;
6. validate `server.json` with `mcp-publisher`;
7. publish the corresponding version to the MCP Registry.

## Release posture

`0.1.0` is a **design preview**, not Production GA.

It is intended to validate a clean MCP integration path for LoopGrid v0.8.x without changing LoopGrid's signing, hash-chain, evidence-bundle, verification, or SDK contracts.

LoopGrid provides signed, tamper-evident evidence and append-only decision history. Verification confirms the integrity of the captured record; it does not determine legal compliance.

## License

Apache-2.0.

See `LICENSE`.
