from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

SITE = "sonoran-west"
ASSETS = ("feeder-01", "primary-crusher-01", "secondary-crusher-01", "screen-01", "conveyor-01", "conveyor-02", "stacker-01", "stockpile-01")
DEFAULT_SCENARIOS = ("gradual_degradation", "isolated_spike", "sensor_drift_frozen", "connectivity_outage", "screen_restriction", "planned_maintenance", "duplicate_replay", "late_out_of_order", "unit_asset_mismatch", "schema_drift", "demand_order_risk")
MAX_WALLCLOCK_SPAN_MINUTES = 60.0


@dataclass(frozen=True)
class SimulationConfig:
    seed: int = 7
    minutes: int = 180
    start_at: datetime = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
    scenarios: tuple[str, ...] = DEFAULT_SCENARIOS
    batch_size: int = 24
    wallclock_span_minutes: float | None = None
    anchor_end: datetime | str | None = None


@dataclass
class PrivateTruth:
    seed: int
    scenario_windows: list[dict[str, Any]] = field(default_factory=list)
    expected_signals: list[dict[str, Any]] = field(default_factory=list)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema": "evaluation-private-1", "seed": self.seed, "scenario_windows": self.scenario_windows, "expected_signals": self.expected_signals}, indent=2, sort_keys=True), encoding="utf-8")


class PlantGenerator:
    """Heuristic, deterministic aggregate-plant generator; not machinery physics."""
    def __init__(self, config: SimulationConfig):
        self.config = config
        self._wallclock_anchor = self._resolve_wallclock_anchor()
        self.rng = random.Random(config.seed)
        self.truth = PrivateTruth(config.seed)
        self._windows = self._schedule()
        self._previous: list[dict[str, Any]] = []

    def _schedule(self) -> dict[str, tuple[int, int, str]]:
        windows: dict[str, tuple[int, int, str]] = {}
        candidates = list(ASSETS)
        for index, scenario in enumerate(self.config.scenarios):
            start = max(5, int(self.config.minutes * (0.12 + (index % 6) * 0.11)) + self.rng.randrange(-3, 4))
            duration = max(3, min(30, self.rng.randrange(5, 18)))
            asset = self.rng.choice(candidates)
            if scenario in {"gradual_degradation", "isolated_spike"}: asset = self.rng.choice(("primary-crusher-01", "secondary-crusher-01"))
            if scenario == "screen_restriction": asset = "screen-01"
            if scenario == "sensor_drift_frozen": asset = self.rng.choice(("primary-crusher-01", "screen-01", "conveyor-01"))
            end = min(self.config.minutes - 1, start + duration)
            windows[scenario] = (start, end, asset)
            self.truth.scenario_windows.append({
                "scenario": scenario,
                "start_minute": start,
                "end_minute": end,
                "start_at": self._iso(self._time_at_step(start)),
                "end_at": self._iso(self._time_at_step(end)),
                "asset": asset,
            })
        return windows

    def _resolve_wallclock_anchor(self) -> datetime | None:
        span, anchor = self.config.wallclock_span_minutes, self.config.anchor_end
        if span is None and anchor is None:
            return None
        if span is None or anchor is None:
            raise ValueError("wallclock_span_minutes and anchor_end must be provided together")
        if not 0 < span <= MAX_WALLCLOCK_SPAN_MINUTES:
            raise ValueError(f"wallclock_span_minutes must be between 0 and {MAX_WALLCLOCK_SPAN_MINUTES:g}")
        if anchor == "now":
            return datetime.now(timezone.utc)
        if isinstance(anchor, str):
            try:
                anchor = datetime.fromisoformat(anchor.replace("Z", "+00:00"))
            except ValueError as error:
                raise ValueError("anchor_end must be 'now' or an ISO-8601 timestamp") from error
        if not isinstance(anchor, datetime) or anchor.tzinfo is None:
            raise ValueError("anchor_end must include a UTC offset")
        return anchor.astimezone(timezone.utc)

    def _time_at_step(self, minute: int) -> datetime:
        if self._wallclock_anchor is None:
            return self.config.start_at + timedelta(minutes=minute)
        if self.config.minutes <= 1:
            return self._wallclock_anchor
        span = timedelta(minutes=self.config.wallclock_span_minutes or 0)
        start = self._wallclock_anchor - span
        return start + span * (minute / (self.config.minutes - 1))

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def batches(self) -> Iterable[dict[str, Any]]:
        current: list[dict[str, Any]] = []
        for minute in range(self.config.minutes):
            for observation in self._observations_for_minute(minute):
                current.append(observation)
                if len(current) >= self.config.batch_size:
                    yield self._batch(current)
                    current = []
        if current:
            yield self._batch(current)

    def _batch(self, observations: list[dict[str, Any]]) -> dict[str, Any]:
        source_type = "telemetry" if all(item["kind"] == "telemetry" for item in observations) else "file"
        return {"contract_version": "1.0", "source": {"source_id": f"synthetic-{source_type}-gateway", "source_type": source_type, "received_via": "api"}, "observations": observations}

    def _active(self, name: str, minute: int) -> tuple[bool, str]:
        window = self._windows.get(name)
        return (bool(window and window[0] <= minute <= window[1]), window[2] if window else "")

    def _observations_for_minute(self, minute: int) -> list[dict[str, Any]]:
        at = self._time_at_step(minute)
        active_screen, _ = self._active("screen_restriction", minute)
        active_degrade, degrade_asset = self._active("gradual_degradation", minute)
        active_spike, spike_asset = self._active("isolated_spike", minute)
        active_outage, outage_asset = self._active("connectivity_outage", minute)
        active_frozen, frozen_asset = self._active("sensor_drift_frozen", minute)
        throughput = 840 + self.rng.gauss(0, 12) - (130 if active_screen else 0) - (35 if active_degrade else 0)
        feed_rate = throughput * (1.03 + self.rng.gauss(0, .01))
        crusher_load = 68 + (10 if active_screen else 0) + (8 if active_degrade else 0)
        rows: list[dict[str, Any]] = []
        for asset, metric, value, unit in [
            ("feeder-01", "feed_rate_tph", feed_rate, "t/h"),
            ("primary-crusher-01", "motor_current_amps", 320 + crusher_load * 1.25 + self.rng.gauss(0, 3), "A"),
            ("primary-crusher-01", "vibration_mm_s", 4.8 + (minute - self._windows.get("gradual_degradation", (minute, minute, ""))[0]) * .17 if active_degrade and degrade_asset == "primary-crusher-01" else 4.8 + self.rng.gauss(0, .3), "mm/s"),
            ("secondary-crusher-01", "motor_current_amps", 260 + crusher_load + self.rng.gauss(0, 3), "A"),
            ("secondary-crusher-01", "vibration_mm_s", 4.1 + (minute - self._windows.get("gradual_degradation", (minute, minute, ""))[0]) * .17 if active_degrade and degrade_asset == "secondary-crusher-01" else 4.1 + self.rng.gauss(0, .25), "mm/s"),
            ("screen-01", "screen_load_percent", 72 + (19 if active_screen else 0) + self.rng.gauss(0, 2), "%"),
            ("conveyor-01", "belt_speed_mps", 2.8 + self.rng.gauss(0, .04), "m/s"),
            ("stacker-01", "stacking_rate_tph", throughput + self.rng.gauss(0, 8), "t/h"),
        ]:
            if active_outage and asset == outage_asset:
                continue
            if active_spike and asset == spike_asset and metric == "vibration_mm_s": value += self.rng.uniform(7, 12)
            if active_frozen and asset == frozen_asset and metric in {"vibration_mm_s", "screen_load_percent"}: value = 5.0 if metric == "vibration_mm_s" else 73.0
            rows.append(self._telemetry(at, minute, asset, metric, round(value, 2), unit))
        rows.extend(self._records(at, minute, throughput, active_screen))
        return self._arrival_variants(rows, minute)

    def _telemetry(self, at: datetime, minute: int, asset: str, metric: str, value: float, unit: str) -> dict[str, Any]:
        return self._observation(at, minute, asset, "telemetry", {"metric": metric, "value": value, "unit": unit, "attributes": {"sample_interval_seconds": 60}})

    def _records(self, at: datetime, minute: int, throughput: float, restricted: bool) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if minute % 15 == 0:
            records.append(self._observation(at, minute, "stockpile-01", "production_record", {"record_type": "production_summary", "attributes": {"throughput_tph": round(throughput, 1), "stockpile_estimate_t": round(4100 + throughput * minute / 60, 1)}}))
        if minute % 30 == 5:
            records.append(self._observation(at, minute, "screen-01", "quality_result", {
                "record_type": "gradation_result",
                "attributes": {"passing_9_5mm_percent": round(61 - (5 if restricted else 0) + self.rng.gauss(0, 1), 1)},
            }))
        maintenance, asset = self._active("planned_maintenance", minute)
        if maintenance and minute == self._windows["planned_maintenance"][0]:
            records.append(self._observation(at, minute, asset, "maintenance_record", {"record_type": "planned_maintenance", "attributes": {"work_order_ref": f"WO-{minute:04d}", "status": "scheduled"}}))
        demand, _ = self._active("demand_order_risk", minute)
        if minute % 20 == 0 or demand:
            records.append(self._observation(at, minute, "stockpile-01", "dispatch_record", {"record_type": "dispatch_order", "attributes": {"requested_tonnes": 1050 if demand else 720, "promised_at": (at + timedelta(hours=2)).isoformat().replace("+00:00", "Z")}}))
        return records

    def _arrival_variants(self, rows: list[dict[str, Any]], minute: int) -> list[dict[str, Any]]:
        duplicate, _ = self._active("duplicate_replay", minute); late, _ = self._active("late_out_of_order", minute); mismatch, _ = self._active("unit_asset_mismatch", minute); drift, _ = self._active("schema_drift", minute)
        if mismatch and rows:
            # A malformed unit is expected to be caught by the current API rule table.
            # Unknown/mismatched identifiers remain public source data, but current API
            # capability has no asset-type registry and therefore accepts them for review.
            target = next((item for item in rows if item["asset_ref"]["asset_id"] == "primary-crusher-01" and item.get("metric") == "vibration_mm_s"), rows[0]).copy()
            target["unit"] = "kW"; target["idempotency_key"] = f"{target['idempotency_key']}-bad-unit"; rows.append(target)
            unknown = next((item for item in rows if item.get("metric") == "motor_current_amps"), rows[0]).copy()
            unknown["asset_ref"] = {"site_id": SITE, "asset_id": "unmapped-sensor-01"}; unknown["idempotency_key"] = f"{unknown['idempotency_key']}-unknown-asset"; rows.append(unknown)
        if drift and rows:
            rows[-1] = {**rows[-1], "attributes": {**rows[-1].get("attributes", {}), "payload_schema_revision": "2.0", "unmodeled_status": "source_extension"}}
        if late and rows:
            target = next((item for item in rows if item["kind"] == "telemetry"), rows[-1]).copy()
            # Append after the current reading, but retain an older source timestamp:
            # this models a late arrival and makes the API's source-time ordering rule observable.
            target["source_recorded_at"] = (datetime.fromisoformat(target["source_recorded_at"].replace("Z", "+00:00")) - timedelta(minutes=8)).isoformat().replace("+00:00", "Z")
            target["idempotency_key"] = f"{target['idempotency_key']}-late-arrival"; rows.append(target)
        if duplicate and self._previous:
            rows.append(self._previous[0].copy())
        self._previous = [row.copy() for row in rows]
        return rows

    def _observation(self, at: datetime, minute: int, asset: str, kind: str, values: dict[str, Any]) -> dict[str, Any]:
        observed_at = at.isoformat().replace("+00:00", "Z")
        material = f"{self.config.seed}:{minute}:{asset}:{kind}:{json.dumps(values, sort_keys=True)}".encode()
        key = hashlib.sha256(material).hexdigest()[:24]
        return {"idempotency_key": f"sim-{key}", "observed_at": observed_at, "asset_ref": {"site_id": SITE, "asset_id": asset}, "kind": kind, "source_recorded_at": observed_at, **values}

    def write_truth(self, path: Path) -> None:
        for item in self.truth.scenario_windows:
            self.truth.expected_signals.append({"window": item, "expected_public_signal": _expected_signal(item["scenario"]), "scoring_class": "evaluation_only"})
        self.truth.save(path)


def _expected_signal(scenario: str) -> str:
    return {"gradual_degradation": "anomaly", "isolated_spike": "anomaly", "sensor_drift_frozen": "data_quality", "connectivity_outage": "data_quality", "screen_restriction": "anomaly", "planned_maintenance": "context_only", "duplicate_replay": "data_quality", "late_out_of_order": "data_quality", "unit_asset_mismatch": "data_quality", "schema_drift": "data_quality", "demand_order_risk": "anomaly"}.get(scenario, "unknown")
