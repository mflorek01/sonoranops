from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import urlopen


@dataclass(frozen=True)
class Score:
    expected: int
    matched: int
    unmatched: list[dict[str, Any]]

    @property
    def recall(self) -> float: return self.matched / self.expected if self.expected else 1.0


def load_export(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_public_api(api_url: str) -> dict[str, Any]:
    """Read-only evaluator path. It deliberately makes no mutation requests."""
    base = api_url.rstrip("/")
    with urlopen(f"{base}/api/v1/findings", timeout=15) as response: findings = json.load(response)
    with urlopen(f"{base}/api/v1/incidents", timeout=15) as response: incidents = json.load(response)
    return {"findings": findings.get("items", findings), "incidents": incidents.get("items", incidents)}


def score(truth: dict[str, Any], platform: dict[str, Any]) -> Score:
    findings = platform.get("findings", [])
    incidents = platform.get("incidents", [])
    expected = [item for item in truth.get("expected_signals", []) if item.get("expected_public_signal") not in {"context_only", "unknown"}]
    unmatched: list[dict[str, Any]] = []
    for item in expected:
        window = item["window"]; signal = item["expected_public_signal"]; asset = window["asset"]
        finding_match = any(finding.get("finding_type") == signal and _asset_matches(finding, asset) for finding in findings)
        incident_match = any(_asset_matches(incident, asset) for incident in incidents)
        if not (finding_match or incident_match): unmatched.append({"asset": asset, "expected_public_signal": signal})
    return Score(expected=len(expected), matched=len(expected) - len(unmatched), unmatched=unmatched)


def _asset_matches(record: dict[str, Any], asset_id: str) -> bool:
    ref = record.get("asset_ref", {})
    refs = record.get("asset_refs", [])
    return ref.get("asset_id") == asset_id or any(item.get("asset_id") == asset_id for item in refs)
