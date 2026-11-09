# Architecture

```text
Hermes MCP ── Anaplan API (not contacted by offline tests)

Local Anaplan exports
       ├── Grammar model loader + dependency graph
       └── Estate CLI ── HTML / JSON / Markdown audit reports
                  ▲
            Analysis MCP (stdio)
```

Hermes remains an independent upstream server. Analysis MCP wraps the pinned Grammar loader/graph API and invokes the pinned Estate CLI. Snapshots and reports are local and confined to `ANAPLAN_DATA_ROOT`; no snapshot collector or automatic model write is implemented. Estate requires Line Items and treats Actions and Modules as optional inputs. A missing optional export is reported as partial coverage, not a validation failure.
