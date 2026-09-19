from pathlib import Path

from loopgrid_mcp.config import Settings


def test_defaults(monkeypatch):
    for key in (
        "LOOPGRID_BASE_URL",
        "LOOPGRID_SERVICE_KEY",
        "LOOPGRID_WORKSPACE",
        "LOOPGRID_MCP_TIMEOUT_SECONDS",
        "LOOPGRID_EVIDENCE_DIR",
        "LOOPGRID_MAX_EVIDENCE_BYTES",
        "LOOPGRID_MCP_ENABLE_REVIEW_TOOL",
        "LOOPGRID_MCP_REVIEWER_ID",
        "LOOPGRID_MCP_ALLOW_PAYLOAD_EXPORT",
    ):
        monkeypatch.delenv(key, raising=False)
    s = Settings.from_env()
    assert s.base_url == "http://127.0.0.1:8000"
    assert s.workspace_id == "default"
    assert s.service_key is None
    assert s.enable_review_tool is False
    assert s.allow_payload_export is False
    assert s.evidence_dir == Path("loopgrid-evidence")


def test_blank_optional_credentials_are_normalized(monkeypatch):
    monkeypatch.setenv("LOOPGRID_SERVICE_KEY", "   ")
    monkeypatch.setenv("LOOPGRID_MCP_REVIEWER_ID", "   ")
    s = Settings.from_env()
    assert s.service_key is None
    assert s.reviewer_id is None
