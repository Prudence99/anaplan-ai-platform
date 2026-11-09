"""Offline end-to-end checks over the actual MCP stdio transport."""
import asyncio
import json
import shutil
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def _data(result):
    if result.structuredContent is not None:
        return result.structuredContent
    for block in result.content:
        if getattr(block, "type", None) == "text":
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                continue
    return None


async def _exercise(tmp_path: Path):
    data_root = tmp_path / "data"
    fixture = ROOT / "data/examples/caldergate-estate"
    shutil.copytree(fixture, data_root / "examples/caldergate-estate")
    snapshot = data_root / "snapshots/caldergate-estate"
    shutil.copytree(fixture / "2 Caldergate FP&A", snapshot)
    (snapshot / "manifest.json").write_text(json.dumps({"model_name": "Caldergate Fictional Example", "created_at": "2026-11-09T00:00:00Z"}), encoding="utf-8")
    (data_root / "snapshots/incomplete").mkdir(parents=True)

    params = StdioServerParameters(
        command=str(ROOT / ".venv/bin/python"),
        args=["-m", "anaplan_platform.mcp.server"],
        cwd=str(ROOT),
        env={"PATH": f"{ROOT / '.venv/bin'}:/usr/bin:/bin", "ANAPLAN_DATA_ROOT": str(data_root), "PYTHONPATH": str(ROOT / "src")},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            expected = {"analyze_formula", "get_formula_references", "audit_model", "get_audit_summary", "get_audit_findings"}
            assert expected <= names

            formula = await session.call_tool("analyze_formula", {"formula": "IF Revenue > 1000 THEN Revenue * 0.1 ELSE 0"})
            assert not formula.isError
            formula_data = _data(formula)
            assert "Revenue" in json.dumps(formula_data)

            refs = await session.call_tool("get_formula_references", {"formula": "Revenue * Price"})
            assert not refs.isError and "Revenue" in json.dumps(_data(refs) or [getattr(x, "text", "") for x in refs.content])

            audit = await session.call_tool("audit_model", {"model_path": str(data_root / "examples/caldergate-estate")})
            assert not audit.isError
            assert (data_root / "reports/caldergate-estate/audit.html").is_file()

            summary = await session.call_tool("get_audit_summary", {"model_name": "caldergate-estate"})
            assert not summary.isError and _data(summary).get("title")

            page1 = await session.call_tool("get_audit_findings", {"model_name": "caldergate-estate", "limit": 3, "offset": 0})
            page2 = await session.call_tool("get_audit_findings", {"model_name": "caldergate-estate", "limit": 3, "offset": 3})
            assert not page1.isError and not page2.isError
            assert _data(page1)["offset"] == 0 and _data(page2)["offset"] == 3
            assert _data(page1)["findings"] != _data(page2)["findings"]

            invalid = await session.call_tool("audit_model", {"model_path": "/etc"})
            assert invalid.isError

            snapshot_result = await session.call_tool("validate_model_snapshot", {"snapshot_id": "caldergate-estate"})
            assert not snapshot_result.isError and _data(snapshot_result)["valid"]
            assert _data(snapshot_result)["coverage"] == "complete"
            graph = await session.call_tool("build_dependency_graph", {"snapshot_id": "caldergate-estate"})
            assert not graph.isError and _data(graph)["stats"]["edges"] > 0
            info = await session.call_tool("get_snapshot_info", {"snapshot_id": "caldergate-estate"})
            assert not info.isError
            snapshots = await session.call_tool("list_model_snapshots", {})
            assert not snapshots.isError and _data(snapshots)["count"] == 2

            nodes = _data(graph)["nodes"]
            source = next((n for n in nodes if n["module"] == "CAL02 Revenue" and n["line_item"] == "Gross Revenue"), None)
            assert source, "Expected known sample line item"
            impact = await session.call_tool("analyze_change_impact", {"snapshot_id": "caldergate-estate", "module_name": source["module"], "line_item_name": source["line_item"]})
            assert not impact.isError and "affected_line_item_count" in json.dumps(_data(impact))
            upstream = await session.call_tool("get_line_item_dependencies", {"snapshot_id": "caldergate-estate", "module_name": source["module"], "line_item_name": source["line_item"]})
            downstream = await session.call_tool("get_line_item_dependents", {"snapshot_id": "caldergate-estate", "module_name": source["module"], "line_item_name": source["line_item"]})
            assert not upstream.isError and not downstream.isError
            missing = await session.call_tool("get_line_item_dependents", {"snapshot_id": "caldergate-estate", "module_name": "missing", "line_item_name": "absent"})
            assert missing.isError
            invalid_snapshot = await session.call_tool("validate_model_snapshot", {"snapshot_id": "../reports"})
            assert invalid_snapshot.isError
            incomplete = await session.call_tool("validate_model_snapshot", {"snapshot_id": "incomplete"})
            assert not incomplete.isError and not _data(incomplete)["valid"]


def test_mcp_stdio_and_offline_features(tmp_path):
    asyncio.run(_exercise(tmp_path))
