from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

EXPECTED_TOOLS = {
    "loopgrid.record_decision",
    "loopgrid.record_review",
    "loopgrid.record_action",
    "loopgrid.record_outcome",
    "loopgrid.get_evidence",
    "loopgrid.verify_evidence",
}


def _loopgrid_env() -> dict[str, str]:
    """Pass only LoopGrid-specific settings to the child MCP process."""
    return {k: v for k, v in os.environ.items() if k.startswith("LOOPGRID_")}


def _structured(result):
    value = getattr(result, "structured_content", None)
    if isinstance(value, dict):
        return value
    # Fallback for clients/servers that return JSON as text content.
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
    return None


async def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "loopgrid_mcp.server"],
        cwd=str(project_root),
        env=_loopgrid_env(),
    )

    print("[INFO] Starting LoopGrid MCP over stdio with the official MCP Python client...")
    async with Client(server) as client:
        print(f"[OK] Connected. Protocol: {client.protocol_version}")
        if client.server_info is not None:
            print(f"[OK] Server: {client.server_info.name} {client.server_info.version}")

        tools_result = await client.list_tools()
        names = {tool.name for tool in tools_result.tools}
        print("[OK] Tools:")
        for name in sorted(names):
            print(f"     {name}")
        missing = EXPECTED_TOOLS - names
        extra = names - EXPECTED_TOOLS
        if missing or extra:
            raise SystemExit(f"Tool mismatch. Missing={sorted(missing)} Extra={sorted(extra)}")

        decision_result = await client.call_tool(
            "loopgrid.record_decision",
            {
                "decision_type": "customer_refund",
                "proposed_action": {
                    "tool": "stripe.refunds.create",
                    "amount": 720,
                    "currency": "USD",
                },
                "agent_id": "mcp-stdio-test-agent",
                "agent_version": "0.1",
                "service_name": "loopgrid-mcp-stdio-test",
                "metadata": {"test": "official-mcp-python-client"},
            },
        )
        if decision_result.is_error:
            raise SystemExit(f"record_decision failed: {decision_result.content}")
        decision = _structured(decision_result)
        if not decision or not decision.get("decision_id"):
            raise SystemExit(f"No decision_id returned: {decision_result.content}")
        decision_id = str(decision["decision_id"])
        print(f"[OK] Decision: {decision_id}")
        print(f"[OK] MCP did not execute the business action: {decision.get('action_executed') is False}")

        action_result = await client.call_tool(
            "loopgrid.record_action",
            {
                "decision_id": decision_id,
                "tool": "stripe.refunds.create",
                "external_reference": "re_mcp_stdio_test",
                "actor_id": "stripe-sandbox",
                "details": {"test": True},
            },
        )
        if action_result.is_error:
            raise SystemExit(f"record_action failed: {action_result.content}")
        print("[OK] Action evidence recorded")

        outcome_result = await client.call_tool(
            "loopgrid.record_outcome",
            {
                "decision_id": decision_id,
                "status": "succeeded",
                "verified_against": "stripe-sandbox",
                "external_reference": "re_mcp_stdio_test",
                "actor_id": "loopgrid-mcp-stdio-test",
                "details": {"test": True},
            },
        )
        if outcome_result.is_error:
            raise SystemExit(f"record_outcome failed: {outcome_result.content}")
        print("[OK] Outcome evidence recorded")

        verify_result = await client.call_tool(
            "loopgrid.verify_evidence", {"decision_id": decision_id}
        )
        if verify_result.is_error:
            raise SystemExit(f"verify_evidence failed: {verify_result.content}")
        verify = _structured(verify_result) or {}
        valid = (verify.get("verification") or {}).get("valid")
        print(f"[OK] Service-side verification valid: {valid}")
        if valid is not True:
            raise SystemExit(f"Verification was not valid: {verify_result.content}")

        evidence_result = await client.call_tool(
            "loopgrid.get_evidence", {"decision_id": decision_id, "include_payloads": False}
        )
        if evidence_result.is_error:
            raise SystemExit(f"get_evidence failed: {evidence_result.content}")
        evidence = _structured(evidence_result) or {}
        bundle_path = (evidence.get("bundle") or {}).get("path")
        print(f"[OK] Evidence exported: {bundle_path}")

        review_result = await client.call_tool(
            "loopgrid.record_review",
            {"decision_id": decision_id, "action": "approve", "reason": "safety test"},
        )
        if review_result.is_error:
            raise SystemExit(f"record_review safety check failed: {review_result.content}")
        review = _structured(review_result) or {}
        print(f"[OK] Review tool remains disabled by default: {review.get('disabled') is True}")
        if review.get("disabled") is not True:
            raise SystemExit("Review tool unexpectedly enabled")

    print("[PASS] Real stdio MCP client test completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
