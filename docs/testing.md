# Offline testing

All tests run without Anaplan credentials and exercise the Analysis MCP through its real stdio transport.

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python scripts/install_example.py
.venv/bin/python -m pytest -q
```

The suite calls formula parsing, Estate audit, summary and paginated findings; validates a sample snapshot; builds the Grammar dependency graph and tests change impact; checks invalid paths and missing objects; and performs MCP initialization, discovery and tool execution over stdio. It does not start Hermes or contact Anaplan.

For a manual stdio session, the project `.mcp.json` starts the same server. MCP Inspector can also launch it with:

```bash
npx @modelcontextprotocol/inspector /workspace/.venv/bin/python -m anaplan_platform.mcp.server
```
