"""Small end-to-end REST smoke test through the same tool-service layer used by MCP.

Requires a running LoopGrid instance. It intentionally avoids human review and
third-party business actions. It records synthetic execution/outcome evidence only.
"""
from __future__ import annotations

import asyncio
import uuid

from loopgrid_mcp.client import LoopGridClient
from loopgrid_mcp.config import Settings
from loopgrid_mcp.tools import LoopGridToolService


async def main() -> None:
    settings = Settings.from_env()
    client = LoopGridClient(settings)
    service = LoopGridToolService(settings, client)

    health = await client.health()
    print("[OK] health", health.get("version"))

    decision = await service.record_decision(
        decision_type="mcp_smoke_test",
        agent_id="loopgrid-mcp-smoke",
        service_name="loopgrid-mcp-smoke",
        proposed_action={"tool": "demo.synthetic_action", "amount": 1, "currency": "USD"},
        model={"provider": "synthetic", "name": "none"},
        context={"purpose": "loopgrid-mcp smoke test"},
        input_data={"synthetic": True},
        idempotency_key=f"loopgrid-mcp-smoke:{uuid.uuid4()}",
    )
    decision_id = decision["decision_id"]
    print("[OK] decision", decision_id)

    await service.record_action(
        decision_id,
        tool="demo.synthetic_action",
        external_reference=f"synthetic-{uuid.uuid4().hex[:8]}",
        actor_id="synthetic-test-system",
        details={"synthetic": True},
    )
    print("[OK] action evidence")

    await service.record_outcome(
        decision_id,
        status="succeeded",
        verified_against="synthetic-test-system",
        actor_id="loopgrid-mcp-smoke",
        details={"synthetic": True},
    )
    print("[OK] outcome evidence")

    verification = await service.verify_evidence(decision_id)
    assert verification["verification"]["valid"] is True
    print("[OK] verification")

    bundle = await service.get_evidence(decision_id, include_payloads=False)
    assert bundle["downloaded"] is True
    print("[OK] evidence", bundle["bundle"]["path"])


if __name__ == "__main__":
    asyncio.run(main())
