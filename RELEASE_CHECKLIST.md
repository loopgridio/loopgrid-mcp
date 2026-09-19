# LoopGrid MCP v0.1.0 release checklist

Use this checklist in order. Do not publish to PyPI or the MCP Registry before the GitHub validation stage is complete.

## A. Final local validation

With LoopGrid running locally on `http://127.0.0.1:8000`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

loopgrid-mcp-doctor
python -m pytest -ra
python .\scripts\release_check.py
python .\scripts\smoke_test.py
python .\scripts\mcp_stdio_test.py
python -m build
```

Release gate:

```text
doctor                    PASS
pytest                    PASS
repository hygiene        PASS
REST smoke test           PASS
real stdio MCP test       PASS
wheel + sdist build       PASS
```

## B. Create the public GitHub repository

Create an empty public repository:

```text
https://github.com/loopgridio/loopgrid-mcp
```

Do not initialize it with another README, `.gitignore` or license if you are pushing this prepared folder.

From the prepared folder:

```powershell
git init
git branch -M main
git add .
git status
git commit -m "Initial LoopGrid MCP v0.1.0 design preview"
git remote add origin https://github.com/loopgridio/loopgrid-mcp.git
git push -u origin main
```

Before `git commit`, inspect `git status` and make sure none of these appear:

```text
.venv/
.env
loopgrid-evidence/
__pycache__/
.pytest_cache/
build/
dist/
*.pyc
local evidence ZIP files
credentials/service keys
```

## C. Public GitHub validation

Wait for all GitHub Actions jobs to pass.

Then test as a stranger from a fresh folder:

```powershell
cd C:\Temp
git clone https://github.com/loopgridio/loopgrid-mcp.git
cd loopgrid-mcp
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest -ra
python .\scripts\release_check.py
python .\scripts\mcp_stdio_test.py
```

Do not reuse the development checkout for this gate.

## D. PyPI publication — later step

Only after the public-clone gate passes:

1. verify the `loopgrid-mcp` name is still available on PyPI;
2. build clean wheel + sdist;
3. inspect package contents/metadata;
4. publish using a dedicated PyPI publishing credential or trusted-publishing workflow;
5. install `loopgrid-mcp==0.1.0` from PyPI into a fresh venv;
6. rerun the stdio client test.

## E. MCP Registry — after PyPI

The Registry name is planned as:

```text
io.github.loopgridio/loopgrid-mcp
```

At publication time:

```text
review current official Registry docs
update registry/server.json.draft if needed
copy it to server.json
mcp-publisher validate server.json
mcp-publisher login github
mcp-publisher publish server.json
```

The README `mcp-name` marker must exactly match the Registry name.

## F. What this release must not claim

Do not describe v0.1.0 as Production GA.

Do not claim the MCP bridge independently proves a downstream action happened simply because a caller recorded action evidence.

Do not claim LoopGrid guarantees compliance or determines legal compliance.

Use language such as:

```text
signed
tamper-evident
cryptographically verifiable
portable evidence
service-side verification
independent/offline verification (only when using the standalone verifier)
```
