from __future__ import annotations

import pytest

pytest.importorskip("mcp")
from mcp import Client  # type: ignore  # noqa: E402

from loopgrid_mcp.config import Settings  # noqa: E402
from loopgrid_mcp.server import build_server  # noqa: E402


class FakeService:
    async def record_decision(self, **kwargs):
        return {"decision_id": "dec_test", "captured": True}

    async def record_review(self, decision_id, action, reason=""):
        return {"decision_id": decision_id, "state": action}

    async def record_action(self, decision_id, tool, external_reference=None, actor_id="external-system", details=None):
        return {"decision_id": decision_id, "recorded": True}

    async def record_outcome(self, decision_id, status, verified_against, external_reference=None, actor_id="loopgrid-mcp", details=None):
        return {"decision_id": decision_id, "recorded": True}

    async def get_evidence(self, decision_id, include_payloads=False):
        return {"decision_id": decision_id, "downloaded": True}

    async def verify_evidence(self, decision_id):
        return {"decision_id": decision_id, "verification": {"valid": True}}


@pytest.mark.anyio
async def test_server_exposes_six_tools():
    server = build_server(Settings(), service=FakeService())
    async with Client(server) as client:
        result = await client.list_tools()
        names = {tool.name for tool in result.tools}
        assert names == {
            "loopgrid.record_decision",
            "loopgrid.record_review",
            "loopgrid.record_action",
            "loopgrid.record_outcome",
            "loopgrid.get_evidence",
            "loopgrid.verify_evidence",
        }
