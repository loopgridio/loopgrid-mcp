from __future__ import annotations

from typing import Any, Literal

from mcp.server import MCPServer

from loopgrid_mcp import __version__
from loopgrid_mcp.config import Settings
from loopgrid_mcp.tools import LoopGridToolService


def build_server(
    settings: Settings | None = None,
    service: LoopGridToolService | None = None,
) -> MCPServer:
    settings = settings or Settings.from_env()
    service = service or LoopGridToolService(settings)

    server = MCPServer(
        name="loopgrid-mcp",
        title="LoopGrid MCP Server",
        version=__version__,
        description=(
            "Thin MCP bridge to LoopGrid decision-evidence infrastructure. "
            "It records and retrieves evidence; it does not execute third-party business actions."
        ),
        website_url="https://github.com/loopgridio/loopgrid-mcp",
    )

    @server.tool(
        name="loopgrid.record_decision",
        description=(
            "Capture a consequential AI/agent decision in LoopGrid. Optionally record model output "
            "and evaluate an existing LoopGrid policy. This records evidence only and does not execute "
            "the proposed action."
        ),
    )
    async def record_decision(
        decision_type: str,
        proposed_action: dict[str, Any],
        agent_id: str = "mcp-agent",
        agent_version: str | None = None,
        service_name: str = "mcp-agent",
        authority: dict[str, Any] | None = None,
        model: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        input_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        privacy_mode: Literal["full", "redacted", "proof_only"] | None = None,
        idempotency_key: str | None = None,
        model_output: dict[str, Any] | None = None,
        policy_id: str | None = None,
    ) -> dict[str, Any]:
        return await service.record_decision(
            decision_type=decision_type,
            proposed_action=proposed_action,
            agent_id=agent_id,
            agent_version=agent_version,
            service_name=service_name,
            authority=authority,
            model=model,
            context=context,
            input_data=input_data,
            metadata=metadata,
            privacy_mode=privacy_mode,
            idempotency_key=idempotency_key,
            model_output=model_output,
            policy_id=policy_id,
        )

    @server.tool(
        name="loopgrid.record_review",
        description=(
            "Record a human approve/reject review in LoopGrid. Disabled by default. The operator must "
            "explicitly enable it and configure reviewer identity; the MCP host should require human confirmation."
        ),
    )
    async def record_review(
        decision_id: str,
        action: Literal["approve", "reject"],
        reason: str = "",
    ) -> dict[str, Any]:
        return await service.record_review(decision_id, action, reason)

    @server.tool(
        name="loopgrid.record_action",
        description=(
            "Record evidence that an external tool/action executed. This does NOT call Stripe, Salesforce, "
            "ServiceNow, or any other business system; it only records execution evidence supplied by the integration."
        ),
    )
    async def record_action(
        decision_id: str,
        tool: str,
        external_reference: str | None = None,
        actor_id: str = "external-system",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await service.record_action(decision_id, tool, external_reference, actor_id, details)

    @server.tool(
        name="loopgrid.record_outcome",
        description=(
            "Record an observed downstream outcome for a decision after execution evidence exists. "
            "The integration is responsible for obtaining the outcome from the real downstream system."
        ),
    )
    async def record_outcome(
        decision_id: str,
        status: str,
        verified_against: str,
        external_reference: str | None = None,
        actor_id: str = "loopgrid-mcp",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await service.record_outcome(
            decision_id,
            status,
            verified_against,
            external_reference,
            actor_id,
            details,
        )

    @server.tool(
        name="loopgrid.get_evidence",
        description=(
            "Download a portable LoopGrid evidence ZIP for a decision to the configured local evidence directory. "
            "Raw disclosure payloads are excluded by default."
        ),
    )
    async def get_evidence(
        decision_id: str,
        include_payloads: bool = False,
    ) -> dict[str, Any]:
        return await service.get_evidence(decision_id, include_payloads)

    @server.tool(
        name="loopgrid.verify_evidence",
        description=(
            "Ask the connected LoopGrid service to verify the decision's signed workspace chain. "
            "For independent offline verification of an exported ZIP, use the standalone LoopGrid verifier."
        ),
    )
    async def verify_evidence(decision_id: str) -> dict[str, Any]:
        return await service.verify_evidence(decision_id)

    return server


# The global object is convenient for the official MCP development tooling.
mcp = build_server()


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
