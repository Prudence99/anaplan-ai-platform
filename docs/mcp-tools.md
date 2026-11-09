# Analysis MCP tools

The server uses `ANAPLAN_DATA_ROOT` (default `data/`). Local export and report paths are confined to that directory.

| Tool | Inputs | Purpose |
|---|---|---|
| `analyze_formula` | `formula` | Parse one formula; return AST, references and normalized form. |
| `get_formula_references` | `formula` | Return parsed formula references. |
| `audit_model` | `model_path` | Run Estate on a local export folder and write HTML, JSON and Markdown reports. |
| `get_audit_summary` | `model_name` | Return compact metadata from a previous audit. |
| `get_audit_findings` | `model_name`, optional `limit` (1–100), `offset` | Read a page of findings. |
| `list_model_snapshots` | none | List folders under `data/snapshots/` and their validation status. |
| `validate_model_snapshot` | `snapshot_id` | Validate one snapshot's required Line Items export and optional exports. |
| `get_snapshot_info` | `snapshot_id` | Return manifest and validation details. |
| `build_dependency_graph` | `snapshot_id` | Build formula edges with the pinned Grammar graph implementation. |
| `get_line_item_dependencies` | `snapshot_id`, `line_item_name`, optional `module_name`, `max_depth` | Query upstream Formula dependencies. |
| `get_line_item_dependents` | same | Query direct and transitive downstream readers. |
| `analyze_change_impact` | same | Return upstream dependencies and direct/indirect downstream impact. |

Node IDs use `Module.Line Item`; provide `module_name` when a name occurs in multiple modules. A graph edge points from a formula to an item it uses. Grammar parse errors are included in the graph response; static references do not prove a business result is correct.

## Examples

```json
{"formula":"Revenue * Price"}
```

```json
{"snapshot_id":"sales_planning","module_name":"CAL Revenue","line_item_name":"Revenue","max_depth":5}
```

Snapshot folders must live under `data/snapshots/<snapshot_id>/`. `Line Items*.csv` is required and must contain a `Formula` column. `Actions*.csv` and `Modules*.csv` are optional; without them Estate reports reduced action/process or module-note coverage.
