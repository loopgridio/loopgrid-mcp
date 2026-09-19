from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from .config import Settings


class LoopGridAPIError(RuntimeError):
    """A safe, human-readable LoopGrid API error."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"LoopGrid API returned HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message


def _safe_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        text = response.text.strip()
        return text[:1000] if text else "request failed"

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail[:1000]
        if isinstance(detail, dict):
            return json.dumps(detail, ensure_ascii=False)[:1000]
        return json.dumps(payload, ensure_ascii=False)[:1000]
    return str(payload)[:1000]



def _path_segment(value: str) -> str:
    """Encode a caller-provided identifier as one URL path segment."""
    return quote(value, safe="")


def _safe_decision_filename(decision_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", decision_id)
    cleaned = cleaned.strip("._") or "decision"
    return f"{cleaned}-evidence.zip"


class LoopGridClient:
    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "loopgrid-mcp/0.1.0",
        }
        if self.settings.service_key:
            headers["X-LoopGrid-Key"] = self.settings.service_key
        return headers

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        async with httpx.AsyncClient(
            base_url=self.settings.base_url,
            timeout=self.settings.timeout_seconds,
            headers=self._headers(),
            transport=self._transport,
            follow_redirects=False,
        ) as client:
            response = await client.request(method, path, json=json_body, params=params)
        if response.is_error:
            raise LoopGridAPIError(response.status_code, _safe_error_message(response))
        try:
            return response.json()
        except Exception as exc:
            raise LoopGridAPIError(response.status_code, "expected JSON response") from exc

    async def health(self) -> dict[str, Any]:
        out = await self._request_json("GET", "/health")
        assert isinstance(out, dict)
        return out

    async def ready(self) -> dict[str, Any]:
        out = await self._request_json("GET", "/ready")
        assert isinstance(out, dict)
        return out

    async def create_decision(self, payload: dict[str, Any]) -> dict[str, Any]:
        out = await self._request_json("POST", "/api/v1/decisions", json_body=payload)
        assert isinstance(out, dict)
        return out

    async def append_event(self, decision_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        out = await self._request_json(
            "POST",
            f"/api/v1/decisions/{_path_segment(decision_id)}/events",
            json_body=payload,
        )
        assert isinstance(out, dict)
        return out

    async def evaluate_policy(
        self,
        workspace_id: str,
        policy_id: str,
        proposed_action: dict[str, Any],
        authority: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        out = await self._request_json(
            "POST",
            f"/api/v1/workspaces/{_path_segment(workspace_id)}/policies/evaluate",
            json_body={
                "policy_id": policy_id,
                "proposed_action": proposed_action,
                "authority": authority or {},
                "context": context or {},
            },
        )
        assert isinstance(out, dict)
        return out

    async def review_decision(self, decision_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        out = await self._request_json(
            "POST",
            f"/api/v1/decisions/{_path_segment(decision_id)}/review",
            json_body=payload,
        )
        assert isinstance(out, dict)
        return out

    async def get_decision(self, decision_id: str) -> dict[str, Any]:
        out = await self._request_json("GET", f"/api/v1/decisions/{_path_segment(decision_id)}")
        assert isinstance(out, dict)
        return out

    async def verify_decision(self, decision_id: str) -> dict[str, Any]:
        out = await self._request_json("GET", f"/api/v1/decisions/{_path_segment(decision_id)}/verify")
        assert isinstance(out, dict)
        return out

    async def download_evidence(self, decision_id: str, *, include_payloads: bool = False) -> dict[str, Any]:
        output_dir = self.settings.evidence_dir.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        destination = output_dir / _safe_decision_filename(decision_id)
        temporary = destination.with_suffix(destination.suffix + ".part")

        headers = self._headers()
        headers["Accept"] = "application/zip"
        total = 0
        digest = hashlib.sha256()

        async with httpx.AsyncClient(
            base_url=self.settings.base_url,
            timeout=self.settings.timeout_seconds,
            headers=headers,
            transport=self._transport,
            follow_redirects=False,
        ) as client:
            async with client.stream(
                "GET",
                f"/api/v1/decisions/{_path_segment(decision_id)}/evidence",
                params={"include_payloads": str(include_payloads).lower()},
            ) as response:
                if response.is_error:
                    await response.aread()
                    raise LoopGridAPIError(response.status_code, _safe_error_message(response))

                try:
                    with temporary.open("wb") as fh:
                        async for chunk in response.aiter_bytes():
                            total += len(chunk)
                            if total > self.settings.max_evidence_bytes:
                                raise RuntimeError(
                                    "Evidence bundle exceeded LOOPGRID_MAX_EVIDENCE_BYTES; download stopped"
                                )
                            fh.write(chunk)
                            digest.update(chunk)
                    temporary.replace(destination)
                except Exception:
                    temporary.unlink(missing_ok=True)
                    raise

        return {
            "decision_id": decision_id,
            "path": str(destination),
            "bytes": total,
            "sha256": digest.hexdigest(),
            "include_payloads": include_payloads,
        }
