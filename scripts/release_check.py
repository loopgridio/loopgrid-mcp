from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()

IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "loopgrid-evidence",
    "build",
    "dist",
}
SECRET_PATTERNS = [
    re.compile(r"\blg_(?:live|test)_[A-Za-z0-9_-]{8,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
LOCAL_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+"),
    re.compile(r"/Users/[^/\s]+/"),
    re.compile(r"/home/[^/\s]+/"),
]
TEXT_SUFFIXES = {".py", ".md", ".toml", ".yml", ".yaml", ".json", ".txt", ".example"}
REQUIRED_GITIGNORE = {
    ".venv/",
    "__pycache__/",
    "*.py[cod]",
    ".pytest_cache/",
    ".env",
    "loopgrid-evidence/",
    "build/",
    "dist/",
    "*.egg-info/",
}


def _iter_source_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.resolve() == SELF:
            continue
        rel = path.relative_to(ROOT)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in {"LICENSE", ".gitignore", ".env.example"}:
            continue
        yield path, rel


def main() -> int:
    failures: list[str] = []

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    missing_ignores = sorted(REQUIRED_GITIGNORE - set(gitignore))
    for entry in missing_ignores:
        failures.append(f".gitignore missing required entry: {entry}")

    for path, rel in _iter_source_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                failures.append(f"possible secret in {rel}: {pattern.pattern}")
        for pattern in LOCAL_PATH_PATTERNS:
            if pattern.search(text):
                failures.append(f"local user path in {rel}")

    if failures:
        print("[FAIL] Repository hygiene check")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("[OK] Repository hygiene check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
