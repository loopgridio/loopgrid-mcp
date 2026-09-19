from __future__ import annotations

from typing import Any, Literal

from .client import LoopGridClient
from .config import Settings


class LoopGridToolService:
    """Business logic behind the MCP tools.

    Keeping this separate from the MCP SDK makes the bridge easy to test and
    prevents coupling LoopGrid core code to MCP implementation details.
    """

    def __init__(self, settings: Settings, client: LoopGridClient | None = None):
        self.settings = settings
        self.client = client or LoopGridClient(settings)

    async def record_decision(
        self,
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
        """Capture a decision and optionally attach model + policy evidence.

        This records evidence only. It does not execute the proposed action.
        """
        agent: dict[str, Any] = {"id": agent_id}
        if agent_version:
            agent["version"] = agent_version

        payload: dict[str, Any] = {
            "decision_type": decision_type,
            "service_name": service_name,
            "workspace_id": self.settings.workspace_id,
            "agent": agent,
            "authority": authority or {},
            "model": model or {},
            "context": context or {},
            "input": input_data or {},
            "proposed_action": proposed_action,
            "metadata": {**(metadata or {}), "source": "loopgrid-mcp"},
        }
        if privacy_mode is not None:
            payload["privacy_mode"] = privacy_mode
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key

        created = await self.client.create_decision(payload)
        decision_id = str(created["decision_id"])
        result: dict[str, Any] = {
            "decision_id": decision_id,
            "captured": True,
            "idempotent_replay": bool(created.get("idempotent_replay")),
            "action_executed": False,
        }

        if result["idempotent_replay"]:
            result["note"] = "Existing idempotent decision returned; no duplicate evidence was appended."
            return result

        if model_output is not None:
            result["model_event"] = await self.client.append_event(
                decision_id,
                {
                    "event_type": "model_completed",
                    "actor_type": "agent",
                    "actor_id": agent_id,
                    "payload": model_output,
                },
            )

        if policy_id:
            evaluation = await self.client.evaluate_policy(
                self.settings.workspace_id,
                policy_id,
                proposed_action,
                authority or {},
                context or {},
            )
            result["policy_evaluation"] = evaluation
            result["policy_event"] = await self.client.append_event(
                decision_id,
                {
                    "event_type": "policy_evaluated",
                    "actor_type": "policy",
                    "actor_id": policy_id,
                    "payload": evaluation,
                },
            )
        return result

    async def record_review(
        self,
        decision_id: str,
        action: Literal["approve", "reject"],
        reason: str = "",
    ) -> dict[str, Any]:
        """Record a human review decision when explicitly enabled by the operator."""
        if not self.settings.enable_review_tool:
            return {
                "recorded": False,
                "disabled": True,
                "decision_id": decision_id,
                "message": (
                    "Human-review tool is disabled by default. Set "
                    "LOOPGRID_MCP_ENABLE_REVIEW_TOOL=true and configure "
                    "LOOPGRID_MCP_REVIEWER_ID only when the MCP host requires human confirmation."
                ),
            }
        if not self.settings.reviewer_id:
            raise RuntimeError(
                "LOOPGRID_MCP_REVIEWER_ID is required when LOOPGRID_MCP_ENABLE_REVIEW_TOOL=true"
            )
        return await self.client.review_decision(
            decision_id,
            {
                "action": action,
                "reviewer": self.settings.reviewer_id,
                "reason": reason,
            },
        )

    async def record_action(
        self,
        decision_id: str,
        tool: str,
        external_reference: str | None = None,
        actor_id: str = "external-system",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record evidence that an external action executed.

        This MCP tool DOES NOT execute the external business action itself.
        """
        payload: dict[str, Any] = {**(details or {}), "tool": tool}
        if external_reference:
            payload["external_reference"] = external_reference
        event = await self.client.append_event(
            decision_id,
            {
                "event_type": "tool_executed",
                "actor_type": "tool",
                "actor_id": actor_id,
                "payload": payload,
            },
        )
        return {
            "decision_id": decision_id,
            "recorded": True,
            "action_executed_by_loopgrid_mcp": False,
            "event": event,
        }

    async def record_outcome(
        self,
        decision_id: str,
        status: str,
        verified_against: str,
        external_reference: str | None = None,
        actor_id: str = "loopgrid-mcp",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an observed downstream outcome supplied by the integration."""
        payload: dict[str, Any] = {
            **(details or {}),
            "status": status,
            "verified_against": verified_against,
        }
        if external_reference:
            payload["external_reference"] = external_reference
        event = await self.client.append_event(
            decision_id,
            {
                "event_type": "outcome_observed",
                "actor_type": "integration",
                "actor_id": actor_id,
                "payload": payload,
            },
        )
        return {
            "decision_id": decision_id,
            "recorded": True,
            "event": event,
        }

    async def get_evidence(
        self,
        decision_id: str,
        include_payloads: bool = False,
    ) -> dict[str, Any]:
        """Download the portable evidence ZIP to the operator-configured evidence directory."""
        if include_payloads and not self.settings.allow_payload_export:
            return {
                "downloaded": False,
                "decision_id": decision_id,
                "message": (
                    "Payload export is disabled by default. Set "
                    "LOOPGRID_MCP_ALLOW_PAYLOAD_EXPORT=true only if disclosure export is intended."
                ),
            }
        bundle = await self.client.download_evidence(decision_id, include_payloads=include_payloads)
        verification = await self.client.verify_decision(decision_id)
        return {
            "downloaded": True,
            "bundle": bundle,
            "server_verification": verification,
            "note": (
                "server_verification asks the connected LoopGrid service to verify the decision. "
                "Use the standalone LoopGrid verifier for out-of-band offline verification."
            ),
        }

    async def verify_evidence(self, decision_id: str) -> dict[str, Any]:
        """Ask the connected LoopGrid service to verify a decision's signed workspace chain."""
        verification = await self.client.verify_decision(decision_id)
        return {
            "decision_id": decision_id,
            "verification": verification,
            "offline_verifier_used": False,
            "note": (
                "This is service-side verification. It is not a substitute for the standalone "
                "offline verifier when independent out-of-band verification is required."
            ),
        }
