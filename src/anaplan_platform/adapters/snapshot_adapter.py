"""Snapshot discovery and input validation for Estate and Grammar."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


class SnapshotAdapter:
    REQUIRED = {"Formula"}
    OPTIONAL_FILES = ("Actions.csv", "Modules.csv")

    def __init__(self, data_root: str | Path):
        self.data_root = Path(data_root).resolve()
        self.root = (self.data_root / "snapshots").resolve()

    def _snapshot(self, snapshot_id: str) -> Path:
        if not snapshot_id or Path(snapshot_id).name != snapshot_id or snapshot_id in {".", ".."}:
            raise ValueError("snapshot_id must be a single directory name")
        path = (self.root / snapshot_id).resolve()
        try:
            path.relative_to(self.data_root)
        except ValueError as exc:
            raise ValueError("Snapshot path is outside configured data directory") from exc
        return path

    def list_model_snapshots(self) -> dict:
        snapshots = []
        if self.root.is_dir():
            for path in sorted(p for p in self.root.iterdir() if p.is_dir()):
                snapshots.append(self.validate_model_snapshot(path.name))
        return {"count": len(snapshots), "snapshots": snapshots}

    def validate_model_snapshot(self, snapshot_id: str) -> dict:
        path = self._snapshot(snapshot_id)
        issues: list[str] = []
        warnings: list[str] = []
        line_files = sorted(path.rglob("Line Items*.csv")) if path.is_dir() else []
        actions_files = sorted(path.rglob("Actions*.csv")) if path.is_dir() else []
        modules_files = sorted(path.rglob("Modules*.csv")) if path.is_dir() else []
        if not path.is_dir():
            issues.append("Snapshot directory not found")
        if not line_files:
            issues.append("Required Line Items*.csv export is missing")
        if len(line_files) > 1:
            issues.append("More than one Line Items export found; keep one per snapshot")
        fields = []
        if len(line_files) == 1:
            try:
                with line_files[0].open("r", encoding="utf-8-sig", newline="") as f:
                    fields = next(csv.reader(f), [])
                if not fields or not any(x.strip() for x in fields):
                    issues.append("Line Items CSV has no header row")
                elif "Formula" not in fields:
                    issues.append("Line Items CSV is missing the required Formula column")
            except (OSError, UnicodeError, csv.Error) as exc:
                issues.append(f"Line Items CSV cannot be read: {exc}")
        for label, files, required_column in (("Actions", actions_files, "Action"), ("Modules", modules_files, None)):
            for optional_file in files:
                try:
                    with optional_file.open("r", encoding="utf-8-sig", newline="") as f:
                        optional_fields = next(csv.reader(f), [])
                    if not optional_fields or not any(x.strip() for x in optional_fields):
                        issues.append(f"{label} CSV has no header row: {optional_file.name}")
                    elif required_column and required_column not in optional_fields:
                        warnings.append(f"{label} CSV lacks '{required_column}' column; some {label.lower()} analyses may be unavailable")
                except (OSError, UnicodeError, csv.Error) as exc:
                    issues.append(f"{label} CSV cannot be read: {optional_file.name}: {exc}")
        if not actions_files:
            warnings.append("Actions.csv is optional; action and process analysis will be incomplete")
        if not modules_files:
            warnings.append("Modules.csv is optional; module notes and some structural checks are unavailable")
        manifest_path = path / "manifest.json"
        manifest = {}
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                warnings.append(f"manifest.json could not be read: {exc}")
        return {
            "snapshot_id": snapshot_id,
            "valid": not issues,
            "coverage": "complete" if not warnings else "partial",
            "issues": issues,
            "warnings": warnings,
            "files": {"line_items": [str(p.relative_to(path)) for p in line_files], "actions": [str(p.relative_to(path)) for p in actions_files], "modules": [str(p.relative_to(path)) for p in modules_files]},
            "line_item_columns": fields,
            "manifest": manifest,
        }

    def get_snapshot_info(self, snapshot_id: str) -> dict:
        result = self.validate_model_snapshot(snapshot_id)
        path = self._snapshot(snapshot_id)
        manifest = result["manifest"]
        result["snapshot_path"] = str(path)
        result["created_at"] = manifest.get("created_at") or (datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if path.exists() else None)
        result["model_name"] = manifest.get("model_name", snapshot_id)
        result["model_id"] = manifest.get("model_id")
        return result
