"""Dependency graph adapter for the pinned anaplan-grammar graph API."""
from __future__ import annotations

from anaplan_grammar.graph import build_graph
from anaplan_grammar.model import load_model

from .snapshot_adapter import SnapshotAdapter


class GrammarAdapter:
    def __init__(self, snapshots: SnapshotAdapter):
        self.snapshots = snapshots
        self._graphs = {}

    def _graph(self, snapshot_id: str):
        info = self.snapshots.validate_model_snapshot(snapshot_id)
        if not info["valid"]:
            raise ValueError("Invalid model snapshot: " + "; ".join(info["issues"]))
        path = (self.snapshots.root / snapshot_id).resolve()
        line_items = next(path.rglob("Line Items*.csv"))
        module_files = sorted(path.rglob("Modules*.csv"))
        stamp = (line_items.stat().st_mtime_ns, line_items.stat().st_size,
                 module_files[0].stat().st_mtime_ns if module_files else None)
        key = (snapshot_id, stamp)
        if key not in self._graphs:
            model = load_model(line_items, module_files[0] if module_files else None, name=snapshot_id)
            self._graphs = {key: build_graph(model)}
        return self._graphs[key]

    @staticmethod
    def _node(key, depth=None):
        node = {"id": f"{key[0]}.{key[1]}", "module": key[0], "line_item": key[1]}
        if depth is not None:
            node["depth"] = depth
        return node

    def build_dependency_graph(self, snapshot_id: str) -> dict:
        graph = self._graph(snapshot_id)
        edges = [{"source": f"{a[0]}.{a[1]}", "target": f"{b[0]}.{b[1]}"}
                 for a, targets in graph.edges.items() for b in sorted(targets)]
        return {"snapshot_id": snapshot_id, "stats": graph.stats(), "nodes": [self._node(k) for k in sorted(graph.model.line_items)], "edges": edges, "parse_errors": [{"id": f"{k[0]}.{k[1]}", "error": v} for k, v in graph.parse_errors.items()]}

    def _resolve(self, graph, module_name: str | None, line_item_name: str):
        if module_name:
            key = (module_name, line_item_name)
            if key not in graph.model.line_items:
                raise ValueError(f"Line item not found: {module_name}.{line_item_name}")
            return key
        matches = [key for key in graph.model.line_items if key[1] == line_item_name]
        if not matches:
            raise ValueError(f"Line item not found: {line_item_name}")
        if len(matches) > 1:
            raise ValueError(f"Line item name is ambiguous; specify module_name: {', '.join(m[0] for m in matches)}")
        return matches[0]

    def get_line_item_dependencies(self, snapshot_id: str, line_item_name: str, module_name: str | None = None, max_depth: int = 5) -> dict:
        graph = self._graph(snapshot_id); key = self._resolve(graph, module_name, line_item_name)
        related = graph.lineage(key, depth=max(1, min(max_depth, 20)))
        return {"snapshot_id": snapshot_id, "source": self._node(key), "dependencies": [self._node(k, d) for k, d in sorted(related.items(), key=lambda item: (item[1], item[0]))], "count": len(related)}

    def get_line_item_dependents(self, snapshot_id: str, line_item_name: str, module_name: str | None = None, max_depth: int = 5) -> dict:
        graph = self._graph(snapshot_id); key = self._resolve(graph, module_name, line_item_name)
        related = graph.impact(key, depth=max(1, min(max_depth, 20)))
        return {"snapshot_id": snapshot_id, "source": self._node(key), "dependents": [self._node(k, d) for k, d in sorted(related.items(), key=lambda item: (item[1], item[0]))], "count": len(related)}

    def analyze_change_impact(self, snapshot_id: str, line_item_name: str, module_name: str | None = None, max_depth: int = 5) -> dict:
        upstream = self.get_line_item_dependencies(snapshot_id, line_item_name, module_name, max_depth)
        downstream = self.get_line_item_dependents(snapshot_id, line_item_name, module_name, max_depth)
        direct = [x for x in downstream["dependents"] if x["depth"] == 1]
        indirect = [x for x in downstream["dependents"] if x["depth"] > 1]
        return {"snapshot_id": snapshot_id, "source": upstream["source"], "dependencies": upstream["dependencies"], "direct_dependents": direct, "indirect_dependents": indirect, "affected_line_item_count": downstream["count"], "max_depth": max(1, min(max_depth, 20)), "parse_errors_in_graph": self._graph(snapshot_id).stats()["parse_errors"]}
