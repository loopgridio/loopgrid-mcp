from __future__ import annotations

import asyncio
import sys

from .client import LoopGridAPIError, LoopGridClient
from .config import Settings


async def _run() -> int:
    try:
        settings = Settings.from_env()
        client = LoopGridClient(settings)
        health = await client.health()
        ready = await client.ready()
    except (LoopGridAPIError, OSError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        return 1
    except Exception as exc:
        print(f"[FAIL] {type(exc).__name__}: {exc}")
        return 1

    print(f"[OK] LoopGrid reachable: {settings.base_url}")
    print(f"[OK] version: {health.get('version', 'unknown')}")
    print(f"[OK] evidence profile: {health.get('evidence_profile', 'unknown')}")
    print(f"[OK] database: {ready.get('database', 'unknown')}")
    print(f"[OK] signer: {ready.get('signer', 'unknown')}")
    print(f"[OK] MCP workspace: {settings.workspace_id}")
    print(f"[INFO] service key configured: {'yes' if settings.service_key else 'no'}")
    print(f"[INFO] human review tool enabled: {'yes' if settings.enable_review_tool else 'no'}")
    print(f"[INFO] raw payload export enabled: {'yes' if settings.allow_payload_export else 'no'}")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
