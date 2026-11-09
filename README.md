# Anaplan AI Engineering Platform

This workspace combines Hermes Anaplan MCP (live model access) with a Python Analysis MCP that wraps Anaplan Grammar and Anaplan Estate. Start with offline exports; configure Hermes credentials only when ready to test a non-production Anaplan account.

## 1. Install and build

Requirements: Python 3.11+, Node.js 18+, npm and Git.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
cd external/hermes-anaplan-mcp
npm ci
npm run build
cd ../..
```

Hermes is pinned to commit `8b00af6`; Grammar to `7834a69`; Estate to `c7f5d3f`. The Python dependencies are installed from those immutable commit IDs.

## 2. Try the offline Estate example

The pinned Estate package ships the fictional Caldergate model under its installed package. This helper copies that example into the local data area:

```bash
.venv/bin/python scripts/install_example.py
```

Then run a local audit, with no Anaplan credentials:

```bash
.venv/bin/python -c 'from anaplan_platform.adapters.estate_adapter import EstateAdapter; print(EstateAdapter().audit_model("examples/caldergate-estate"))'
```

Reports are written to `data/reports/caldergate-estate/` as HTML, JSON and Markdown. Open the HTML file in a browser. MCP paths are confined to `ANAPLAN_DATA_ROOT` (default: `./data`).

## 3. Check formula parsing

```bash
.venv/bin/python -c 'from anaplan_grammar import parse, references, unparse; ast=parse("Revenue * Price"); print({"ast": ast, "references": references(ast), "normalized": unparse(ast)})'
```

## 4. Connect the MCP servers

`.mcp.json` defines two stdio servers: `anaplan-live` (Hermes) and `anaplan-analysis` (this package). The client must support `${PROJECT_ROOT}` expansion and project-level MCP configuration. Otherwise replace it with the absolute workspace path. Hermes credentials are loaded according to `external/hermes-anaplan-mcp/.env.example` and its `config.yaml`; do not commit secrets. Configure credentials only for a non-production, read-only validation first.

The Analysis server exposes formula analysis, Estate audit/report tools, snapshot validation, dependency graph queries and change impact. For a step-by-step tool list and examples, see [docs/mcp-tools.md](docs/mcp-tools.md).

## Offline integration tests

```bash
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

The tests use the fictional Caldergate export, exercise the Analysis MCP over stdio, and do not connect to Anaplan. See [docs/testing.md](docs/testing.md).

## 5. Hermes authentication

Review the current Hermes `.env.example` and `config.yaml`. Copy required region-prefixed OAuth, certificate or basic-auth fields into an untracked environment file in the location Hermes expects. Use a test account with read permissions first. Verify Workspace and Model discovery before trying any operation that changes data.

## Scope

The initial integration supports manual/local standard model exports. Hermes discovery does not automatically create an Estate snapshot; export the required Anaplan files (especially Line Items, optionally Actions and Modules) into a folder under `data/` before auditing. No production model changes are automated.
