from __future__ import annotations

import httpx
import pytest

from loopgrid_mcp.client import LoopGridClient
from loopgrid_mcp.config import Settings


@pytest.mark.anyio
async def test_decision_id_is_encoded_as_single_url_segment():
    seen: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.raw_path.decode("ascii"))
        return httpx.Response(200, json={"valid": True})

    client = LoopGridClient(Settings(), transport=httpx.MockTransport(handler))
    await client.verify_decision("dec_x/../../unexpected")

    assert seen == ["/api/v1/decisions/dec_x%2F..%2F..%2Funexpected/verify"]
