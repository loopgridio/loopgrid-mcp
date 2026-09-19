from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the thin MCP-to-LoopGrid bridge.

    The target LoopGrid URL is configured by the operator, never supplied by an
    MCP tool call. This prevents a model from redirecting the bridge to arbitrary
    hosts.
    """

    base_url: str = "http://127.0.0.1:8000"
    service_key: str | None = None
    workspace_id: str = "default"
    timeout_seconds: float = 20.0
    evidence_dir: Path = Path("loopgrid-evidence")
    max_evidence_bytes: int = 50 * 1024 * 1024
    enable_review_tool: bool = False
    reviewer_id: str | None = None
    allow_payload_export: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        base_url = os.getenv("LOOPGRID_BASE_URL", "http://127.0.0.1:8000").strip().rstrip("/")
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("LOOPGRID_BASE_URL must start with http:// or https://")

        workspace_id = os.getenv("LOOPGRID_WORKSPACE", "default").strip() or "default"
        timeout_raw = os.getenv("LOOPGRID_MCP_TIMEOUT_SECONDS", "20")
        try:
            timeout = float(timeout_raw)
        except ValueError as exc:
            raise ValueError("LOOPGRID_MCP_TIMEOUT_SECONDS must be numeric") from exc
        if timeout <= 0:
            raise ValueError("LOOPGRID_MCP_TIMEOUT_SECONDS must be greater than zero")

        evidence_dir = Path(os.getenv("LOOPGRID_EVIDENCE_DIR", "loopgrid-evidence")).expanduser()
        max_bytes = _env_int("LOOPGRID_MAX_EVIDENCE_BYTES", 50 * 1024 * 1024)
        if max_bytes <= 0:
            raise ValueError("LOOPGRID_MAX_EVIDENCE_BYTES must be greater than zero")

        return cls(
            base_url=base_url,
            service_key=(os.getenv("LOOPGRID_SERVICE_KEY") or "").strip() or None,
            workspace_id=workspace_id,
            timeout_seconds=timeout,
            evidence_dir=evidence_dir,
            max_evidence_bytes=max_bytes,
            enable_review_tool=_env_bool("LOOPGRID_MCP_ENABLE_REVIEW_TOOL", False),
            reviewer_id=(os.getenv("LOOPGRID_MCP_REVIEWER_ID") or "").strip() or None,
            allow_payload_export=_env_bool("LOOPGRID_MCP_ALLOW_PAYLOAD_EXPORT", False),
        )
