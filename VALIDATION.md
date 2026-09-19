# Validation record — v0.1.0 design preview

Date: 2026-09-19

## Windows end-to-end validation of the working candidate

The pre-release working candidate was validated locally on Windows against the public LoopGrid `0.8.1-design-partner` container.

Passed:

- editable install in Python 3.12 venv;
- `loopgrid-mcp-doctor` connectivity/readiness;
- unit + MCP protocol suite: `9 passed`;
- synthetic REST smoke test;
- decision creation;
- action-evidence recording;
- outcome-evidence recording;
- service-side verification;
- evidence ZIP export;
- review tool disabled by default;
- real stdio MCP E2E using the official MCP Python client.

The real stdio run negotiated MCP protocol `2026-07-28`, identified the server as `loopgrid-mcp 0.1.0`, discovered all six tools, completed decision/action/outcome/verify/export, and ended with:

```text
[PASS] Real stdio MCP client test completed successfully.
```

Tools discovered:

```text
loopgrid.get_evidence
loopgrid.record_action
loopgrid.record_decision
loopgrid.record_outcome
loopgrid.record_review
loopgrid.verify_evidence
```

## GitHub-ready hardening performed after that pass

The final GitHub-ready candidate adds:

- canonical action fields protected from free-form `details` overrides;
- canonical outcome fields protected from free-form `details` overrides;
- MCP provenance metadata protected from caller override;
- caller-provided URL-path identifiers encoded as one path segment;
- cross-platform GitHub Actions coverage for Ubuntu, Windows and macOS;
- package-build/install verification;
- repository hygiene checks for obvious secrets/local user paths;
- updated `loopgridio/loopgrid-mcp` repository and MCP Registry namespace metadata.

In the offline build environment used to assemble this GitHub-ready package:

```text
repository hygiene check        PASS
non-MCP/unit hardening tests    13 passed
MCP protocol test               skipped (mcp package unavailable in offline build environment)
wheel build                     PASS
wheel metadata/contents review  PASS
```

The hardening changes are small and do not alter LoopGrid core, its database schema, signing implementation, hash chain, evidence bundle or verifier contract. Nevertheless, this final package must receive one fresh Windows rerun before the GitHub push. With the MCP dependency installed, the expected final pytest count is **14 passed**.

## Inspector note

The browser Inspector was not used as the release gate on the tested Windows machine because the then-current Inspector npm installation hit an optional native-binding issue. A deprecated v1 Inspector could launch, but the stronger direct protocol test using the official current MCP Python client over stdio passed.

Node.js and the Inspector are not required for normal `loopgrid-mcp` stdio operation.

## Before public GitHub publication

Run from this final package with LoopGrid running:

```powershell
loopgrid-mcp-doctor
python -m pytest -ra
python .\scripts\release_check.py
python .\scripts\smoke_test.py
python .\scripts\mcp_stdio_test.py
python -m build
```

Expected release gate:

```text
doctor                    PASS
pytest                    14 passed
repository hygiene        PASS
REST smoke test           PASS
real stdio MCP test       PASS
wheel + sdist build       PASS
```

## Before PyPI / MCP Registry publication

Also require:

1. green GitHub Actions from a clean public checkout;
2. successful install of the built wheel in a clean environment;
3. public PyPI package published as `loopgrid-mcp`;
4. Registry metadata revalidated against the current official schema;
5. PyPI README ownership marker exactly matching the Registry server name.

## Release posture

This is a design preview, not Production GA. Verification confirms integrity of the captured record; it does not by itself prove that an external-world claim is true or determine legal compliance.
