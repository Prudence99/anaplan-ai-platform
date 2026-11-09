"""MCP tools exposing the Anaplan formula analysis libraries."""

from mcp.server.fastmcp import FastMCP
from anaplan_platform.adapters.estate_adapter import EstateAdapter
from anaplan_platform.adapters.snapshot_adapter import SnapshotAdapter
from anaplan_platform.adapters.grammar_adapter import GrammarAdapter

server = FastMCP("anaplan-analysis")
estate = EstateAdapter()
snapshots = SnapshotAdapter(estate.data_root)
grammar = GrammarAdapter(snapshots)


def _grammar():
    try:
        from anaplan_grammar import parse, references, unparse
    except ImportError as exc:
        raise RuntimeError("Install the project dependencies to use formula analysis") from exc
    return parse, references, unparse


@server.tool()
def analyze_formula(formula: str) -> dict:
    """Parse an Anaplan formula and return its AST, references and normalized form."""
    parse, references, unparse = _grammar()
    ast = parse(formula)
    return {"formula": formula, "ast": ast, "references": references(ast), "normalized_formula": unparse(ast)}


@server.tool()
def get_formula_references(formula: str) -> list:
    """Extract referenced line items or expressions from an Anaplan formula."""
    return analyze_formula(formula)["references"]


@server.tool()
def audit_model(model_path: str) -> dict:
    """Audit a local Anaplan export folder and create compact report files.

    Paths are restricted to ANAPLAN_DATA_ROOT (default: ./data).
    """
    return estate.audit_model(model_path)


@server.tool()
def get_audit_summary(model_name: str) -> dict:
    """Read a compact summary from an existing audit report."""
    return estate.get_audit_summary(model_name)


@server.tool()
def get_audit_findings(model_name: str, limit: int = 20, offset: int = 0) -> dict:
    """Read up to 100 findings from a completed Estate audit report."""
    return estate.get_audit_findings(model_name, limit, offset)


@server.tool()
def list_model_snapshots() -> dict:
    """List model snapshots stored under data/snapshots."""
    return snapshots.list_model_snapshots()


@server.tool()
def validate_model_snapshot(snapshot_id: str) -> dict:
    """Check required Line Items export and optional Actions/Modules coverage."""
    return snapshots.validate_model_snapshot(snapshot_id)


@server.tool()
def get_snapshot_info(snapshot_id: str) -> dict:
    """Return manifest metadata and validation details for a snapshot."""
    return snapshots.get_snapshot_info(snapshot_id)


@server.tool()
def build_dependency_graph(snapshot_id: str) -> dict:
    """Build Formula dependencies from the snapshot's Anaplan CSV exports."""
    return grammar.build_dependency_graph(snapshot_id)


@server.tool()
def get_line_item_dependencies(snapshot_id: str, line_item_name: str, module_name: str | None = None, max_depth: int = 5) -> dict:
    """Get upstream Formula references; specify module_name for duplicate names."""
    return grammar.get_line_item_dependencies(snapshot_id, line_item_name, module_name, max_depth)


@server.tool()
def get_line_item_dependents(snapshot_id: str, line_item_name: str, module_name: str | None = None, max_depth: int = 5) -> dict:
    """Get direct and transitive downstream Formula readers."""
    return grammar.get_line_item_dependents(snapshot_id, line_item_name, module_name, max_depth)


@server.tool()
def analyze_change_impact(snapshot_id: str, line_item_name: str, module_name: str | None = None, max_depth: int = 5) -> dict:
    """Summarize upstream dependencies and downstream impact of a change."""
    return grammar.analyze_change_impact(snapshot_id, line_item_name, module_name, max_depth)


if __name__ == "__main__":
    server.run()
