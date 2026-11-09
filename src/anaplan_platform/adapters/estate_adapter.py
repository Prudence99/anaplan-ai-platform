"""Run Anaplan Estate's supported CLI and expose bounded report access."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


class EstateAdapter:
    def __init__(self, data_root: str | Path | None = None, timeout: int = 300):
        self.data_root = Path(data_root or os.environ.get("ANAPLAN_DATA_ROOT", "data")).resolve()
        self.timeout = timeout

    def _model_dir(self, model_path: str) -> Path:
        candidate = Path(model_path)
        if not candidate.is_absolute():
            candidate = self.data_root / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(self.data_root)
        except ValueError as exc:
            raise ValueError(f"Model path must be inside configured data directory: {self.data_root}") from exc
        if not candidate.is_dir():
            raise ValueError(f"Model directory not found: {candidate}")
        if not any(candidate.rglob("Line Items*.csv")):
            raise ValueError("Model directory must contain a 'Line Items*.csv' export")
        return candidate

    @staticmethod
    def _cli() -> str:
        executable = Path(sys.executable).with_name("anaplan-estate")
        cli = str(executable) if executable.exists() else shutil.which("anaplan-estate")
        if not cli:
            raise RuntimeError("Estate CLI not found. Install the project in its virtual environment with pip install -e .")
        return cli

    def audit_model(self, model_path: str) -> dict:
        model_dir = self._model_dir(model_path)
        report_dir = self.data_root / "reports" / model_dir.name
        report_dir.mkdir(parents=True, exist_ok=True)
        json_path = report_dir / "audit.json"
        html_path = report_dir / "audit.html"
        markdown_path = report_dir / "audit.md"
        command = [self._cli(), str(model_dir), "--json", str(json_path), "--html", str(html_path), "--out", str(markdown_path)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Estate audit exceeded {self.timeout} seconds") from exc
        if result.returncode:
            detail = (result.stderr or result.stdout)[-2000:]
            raise RuntimeError(f"Estate audit failed (exit {result.returncode}): {detail}")
        if not json_path.is_file():
            raise RuntimeError("Estate completed without creating its JSON report")
        try:
            with json_path.open(encoding="utf-8") as report_file:
                report = json.load(report_file)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Estate created an unreadable JSON report: {exc}") from exc
        return {
            "status": "success",
            "model_path": str(model_dir),
            "html_path": str(html_path),
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
            "summary": self._summary(report),
        }

    def get_audit_summary(self, model_name: str) -> dict:
        report = self._read_report(model_name)
        return self._summary(report)

    def get_audit_findings(self, model_name: str, limit: int = 20, offset: int = 0) -> dict:
        report = self._read_report(model_name)
        findings = report.get("findings", report.get("checks", []))
        if isinstance(findings, dict):
            findings = list(findings.values())
        if not isinstance(findings, list):
            findings = []
        page_size = max(1, min(limit, 100))
        start = max(0, offset)
        return {"model_name": model_name, "total": len(findings), "offset": start, "limit": page_size, "findings": findings[start:start + page_size]}

    def _read_report(self, model_name: str) -> dict:
        if not model_name or Path(model_name).name != model_name or model_name in {".", ".."}:
            raise ValueError("model_name must be a single report directory name")
        report_path = self.data_root / "reports" / model_name / "audit.json"
        if not report_path.is_file():
            raise ValueError(f"No audit report found for '{model_name}'; run audit_model first")
        with report_path.open(encoding="utf-8") as report_file:
            return json.load(report_file)

    @staticmethod
    def _summary(report: dict) -> dict:
        # Keep report summaries compact and preserve data coverage caveats.
        models = []
        for model in report.get("models", [])[:20]:
            facts = model.get("facts", {})
            models.append({"name": model.get("name"), "line_items": facts.get("line_items"), "modules": facts.get("modules"), "findings": facts.get("findings"), "parse_errors": facts.get("parse_errors"), "parse_rate": facts.get("parse_rate")})
        return {"title": report.get("title"), "summary": report.get("summary_text"), "models": models, "coverage": report.get("coverage") or report.get("limitations"), "findings_count": len(report.get("findings", [])), "checks_count": len(report.get("checks", []))}
