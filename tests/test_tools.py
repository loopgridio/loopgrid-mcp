from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from loopgrid_mcp.client import LoopGridClient
from loopgrid_mcp.config import Settings
from loopgrid_mcp.tools import LoopGridToolService


@pytest.mark.anyio
async def test_record_decision_with_policy_and_model():
    calls: list[tuple[str, str, dict | None]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        calls.append((request.method, request.url.path, body))
        if request.url.path == "/api/v1/decisions":
            return httpx.Response(200, json={"decision_id": "dec_1", "idempotent_replay": False})
        if request.url.path == "/api/v1/workspaces/default/policies/evaluate":
            return httpx.Response(200, json={"policy_id": "refund-policy", "version": "17.3", "decision": "auto_allowed"})
        if request.url.path == "/api/v1/decisions/dec_1/events":
            return httpx.Response(200, json={"event_id": f"ev_{len(calls)}"})
        return httpx.Response(404, json={"detail": "not found"})

    settings = Settings(service_key="secret")
    client = LoopGridClient(settings, transport=httpx.MockTransport(handler))
    service = LoopGridToolService(settings, client)
    out = await service.record_decision(
        "customer_refund",
        {"tool": "stripe.refunds.create", "amount": 20},
        model_output={"response": "refund proposed"},
        policy_id="refund-policy",
    )

    assert out["decision_id"] == "dec_1"
    assert out["action_executed"] is False
    assert [x[1] for x in calls] == [
        "/api/v1/decisions",
        "/api/v1/decisions/dec_1/events",
        "/api/v1/workspaces/default/policies/evaluate",
        "/api/v1/decisions/dec_1/events",
    ]
    # Secret is only sent as a header; it is never added to the JSON body.
    assert all("secret" not in json.dumps(body or {}) for _, _, body in calls)


@pytest.mark.anyio
async def test_review_disabled_by_default():
    settings = Settings()
    service = LoopGridToolService(settings)
    out = await service.record_review("dec_1", "approve", "ok")
    assert out["disabled"] is True
    assert out["recorded"] is False


@pytest.mark.anyio
async def test_review_uses_operator_configured_identity():
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"decision_id": "dec_1", "state": "approve", "review": {}})

    settings = Settings(enable_review_tool=True, reviewer_id="human@example.com")
    client = LoopGridClient(settings, transport=httpx.MockTransport(handler))
    service = LoopGridToolService(settings, client)
    out = await service.record_review("dec_1", "approve", "checked")
    assert out["state"] == "approve"
    assert captured["reviewer"] == "human@example.com"


@pytest.mark.anyio
async def test_action_and_outcome_are_evidence_only():
    bodies: list[dict] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"event_id": f"ev_{len(bodies)}"})

    settings = Settings()
    client = LoopGridClient(settings, transport=httpx.MockTransport(handler))
    service = LoopGridToolService(settings, client)

    action = await service.record_action("dec_1", "stripe.refunds.create", "re_1", "stripe")
    outcome = await service.record_outcome("dec_1", "succeeded", "stripe-sandbox", "re_1")

    assert action["action_executed_by_loopgrid_mcp"] is False
    assert bodies[0]["event_type"] == "tool_executed"
    assert bodies[1]["event_type"] == "outcome_observed"
    assert outcome["recorded"] is True


@pytest.mark.anyio
async def test_verify_evidence_is_explicitly_service_side():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"valid": True, "checked_events": 2})

    settings = Settings()
    client = LoopGridClient(settings, transport=httpx.MockTransport(handler))
    service = LoopGridToolService(settings, client)
    out = await service.verify_evidence("dec_1")
    assert out["verification"]["valid"] is True
    assert out["offline_verifier_used"] is False


@pytest.mark.anyio
async def test_evidence_download_blocks_payloads_by_default(tmp_path: Path):
    settings = Settings(evidence_dir=tmp_path, allow_payload_export=False)
    service = LoopGridToolService(settings)
    out = await service.get_evidence("dec_1", include_payloads=True)
    assert out["downloaded"] is False


@pytest.mark.anyio
async def test_evidence_download_writes_zip_and_hash(tmp_path: Path):
    zip_bytes = b"PK\x03\x04synthetic-evidence"

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/evidence"):
            return httpx.Response(200, content=zip_bytes, headers={"content-type": "application/zip"})
        if request.url.path.endswith("/verify"):
            return httpx.Response(200, json={"valid": True, "checked_events": 2})
        return httpx.Response(404, json={"detail": "not found"})

    settings = Settings(evidence_dir=tmp_path)
    client = LoopGridClient(settings, transport=httpx.MockTransport(handler))
    service = LoopGridToolService(settings, client)
    out = await service.get_evidence("../dec/unsafe", include_payloads=False)
    assert out["downloaded"] is True
    p = Path(out["bundle"]["path"])
    assert p.parent == tmp_path.resolve()
    assert p.exists()
    assert ".." not in p.name

@pytest.mark.anyio
async def test_free_form_details_cannot_override_canonical_action_fields():
    bodies: list[dict] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"event_id": "ev_1"})

    settings = Settings()
    client = LoopGridClient(settings, transport=httpx.MockTransport(handler))
    service = LoopGridToolService(settings, client)

    await service.record_action(
        "dec_1",
        "stripe.refunds.create",
        details={"tool": "spoofed.tool", "note": "kept"},
    )
    assert bodies[0]["payload"]["tool"] == "stripe.refunds.create"
    assert bodies[0]["payload"]["note"] == "kept"


@pytest.mark.anyio
async def test_free_form_details_cannot_override_canonical_outcome_fields():
    bodies: list[dict] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"event_id": "ev_1"})

    settings = Settings()
    client = LoopGridClient(settings, transport=httpx.MockTransport(handler))
    service = LoopGridToolService(settings, client)

    await service.record_outcome(
        "dec_1",
        "succeeded",
        "stripe-sandbox",
        details={"status": "failed", "verified_against": "spoofed", "note": "kept"},
    )
    assert bodies[0]["payload"]["status"] == "succeeded"
    assert bodies[0]["payload"]["verified_against"] == "stripe-sandbox"
    assert bodies[0]["payload"]["note"] == "kept"

@pytest.mark.anyio
async def test_caller_metadata_cannot_override_mcp_source():
    bodies: list[dict] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"decision_id": "dec_1", "idempotent_replay": False})

    settings = Settings()
    client = LoopGridClient(settings, transport=httpx.MockTransport(handler))
    service = LoopGridToolService(settings, client)

    await service.record_decision(
        "customer_refund",
        {"tool": "stripe.refunds.create"},
        metadata={"source": "spoofed", "note": "kept"},
    )
    assert bodies[0]["metadata"]["source"] == "loopgrid-mcp"
    assert bodies[0]["metadata"]["note"] == "kept"
