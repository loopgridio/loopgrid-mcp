# MCP Registry publishing — deliberately not active yet

`server.json.draft` is preparation only. Do **not** publish it before the package exists on PyPI and public CI is green.

The intended Registry identity is:

```text
io.github.loopgridio/loopgrid-mcp
```

The PyPI README ownership marker must match exactly:

```text
mcp-name: io.github.loopgridio/loopgrid-mcp
```

## Publish gate

Before Registry publication require:

1. `loopgrid-mcp` 0.1.0 published to official PyPI;
2. public GitHub CI green from a clean checkout;
3. real stdio MCP client test green against LoopGrid;
4. `server.json.draft` reviewed against the current official schema;
5. copy/update the draft to `server.json` only at publication time;
6. run `mcp-publisher validate server.json`;
7. authenticate with the GitHub identity that has permission for the `loopgridio` organization namespace;
8. run `mcp-publisher publish server.json`;
9. query the Registry to confirm the published entry.

The official Registry is currently a preview service, so re-check the schema and publisher instructions immediately before publication rather than assuming this draft will remain unchanged.
