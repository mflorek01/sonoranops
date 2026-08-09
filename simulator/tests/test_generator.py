from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sonoran_sim.contract import FORBIDDEN_PRIVATE_TERMS, SCHEMA_PATH, validate_batch
from sonoran_sim.generator import PlantGenerator, SimulationConfig
from sonoran_sim.publisher import JsonlPublisher


def rendered(config: SimulationConfig) -> list[dict]: return list(PlantGenerator(config).batches())


class GeneratorTests(unittest.TestCase):
    def test_same_seed_is_byte_stable(self) -> None:
        config = SimulationConfig(seed=23, minutes=70)
        self.assertEqual(json.dumps(rendered(config), sort_keys=True), json.dumps(rendered(config), sort_keys=True))

    def test_explicit_wallclock_anchor_is_deterministic(self) -> None:
        config = SimulationConfig(
            seed=23,
            minutes=70,
            wallclock_span_minutes=4,
            anchor_end="2026-08-08T18:00:00Z",
        )
        self.assertEqual(
            json.dumps(rendered(config), sort_keys=True),
            json.dumps(rendered(config), sort_keys=True),
        )

    def test_live_compressed_normal_data_stays_in_recent_window(self) -> None:
        before = datetime.now(timezone.utc)
        batches = rendered(SimulationConfig(
            seed=24,
            minutes=50,
            scenarios=(),
            wallclock_span_minutes=4,
            anchor_end="now",
        ))
        after = datetime.now(timezone.utc)
        times = [
            datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00"))
            for batch in batches for item in batch["observations"]
        ]
        self.assertGreaterEqual(min(times), before - timedelta(minutes=4, seconds=1))
        self.assertLessEqual(max(times), after)
        self.assertTrue(all(
            item["source_recorded_at"] == item["observed_at"]
            for batch in batches for item in batch["observations"]
        ))

    def test_compressed_late_scenario_remains_old_and_ordered(self) -> None:
        anchor = datetime(2026, 8, 8, 18, 0, tzinfo=timezone.utc)
        observations = [
            item
            for batch in rendered(SimulationConfig(
                seed=25,
                minutes=30,
                scenarios=("late_out_of_order",),
                wallclock_span_minutes=4,
                anchor_end=anchor,
            ))
            for item in batch["observations"]
        ]
        normal_times = [
            datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00"))
            for item in observations if not item["idempotency_key"].endswith("-late-arrival")
        ]
        late = [item for item in observations if item["idempotency_key"].endswith("-late-arrival")]
        self.assertEqual((min(normal_times), max(normal_times)), (anchor - timedelta(minutes=4), anchor))
        self.assertTrue(late)
        self.assertTrue(all(
            datetime.fromisoformat(item["source_recorded_at"].replace("Z", "+00:00"))
            == datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00")) - timedelta(minutes=8)
            for item in late
        ))
        self.assertLess(
            min(datetime.fromisoformat(item["source_recorded_at"].replace("Z", "+00:00")) for item in late),
            min(normal_times),
        )

    def test_truth_windows_align_with_compressed_public_timestamps(self) -> None:
        generator = PlantGenerator(SimulationConfig(
            seed=26,
            minutes=50,
            scenarios=("gradual_degradation", "isolated_spike"),
            wallclock_span_minutes=4,
            anchor_end="2026-08-08T18:00:00Z",
        ))
        observations = [item for batch in generator.batches() for item in batch["observations"]]
        public_times = {item["observed_at"] for item in observations}
        for window in generator.truth.scenario_windows:
            self.assertIn(window["start_at"], public_times)
            self.assertIn(window["end_at"], public_times)

    def test_compressed_public_output_does_not_leak_private_fields(self) -> None:
        public = json.dumps(rendered(SimulationConfig(
            seed=27,
            minutes=40,
            wallclock_span_minutes=4,
            anchor_end="2026-08-08T18:00:00Z",
        ))).lower()
        self.assertTrue(all(term not in public for term in FORBIDDEN_PRIVATE_TERMS))

    def test_multiple_seeds_are_contract_conformant_and_vary(self) -> None:
        fingerprints = set()
        for seed in (1, 9, 31):
            batches = rendered(SimulationConfig(seed=seed, minutes=80))
            for batch in batches: validate_batch(batch)
            fingerprints.add(json.dumps(batches, sort_keys=True))
        self.assertEqual(len(fingerprints), 3)

    def test_non_telemetry_records_use_root_record_type_and_shared_schema(self) -> None:
        batches = rendered(SimulationConfig(seed=13, minutes=40))
        self.assertTrue(SCHEMA_PATH.is_file())
        records = [item for batch in batches for item in batch["observations"] if item["kind"] != "telemetry"]
        self.assertTrue(records)
        self.assertTrue(all(item.get("record_type") for item in records))
        self.assertTrue(all("record_type" not in item["attributes"] for item in records))
        for batch in batches:
            validate_batch(batch)

    def test_private_truth_never_leaks_to_published_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "public" / "observations.jsonl"; truth = Path(directory) / "evaluator-only" / "truth.json"
            generator = PlantGenerator(SimulationConfig(seed=5, minutes=65))
            publisher = JsonlPublisher(output)
            for batch in generator.batches(): publisher.publish(batch)
            generator.write_truth(truth)
            public = output.read_text(encoding="utf-8").lower(); private = truth.read_text(encoding="utf-8").lower()
            self.assertTrue(all(term not in public for term in FORBIDDEN_PRIVATE_TERMS))
            self.assertIn("scenario_windows", private)
            self.assertIn("expected_signals", private)

    def test_all_requested_source_families_exist(self) -> None:
        observations = [item for batch in rendered(SimulationConfig(seed=11, minutes=90)) for item in batch["observations"]]
        self.assertTrue({"telemetry", "production_record", "quality_result", "maintenance_record", "dispatch_record"}.issubset({item["kind"] for item in observations}))

    def test_late_variant_changes_source_time_and_keeps_unique_key(self) -> None:
        batches = rendered(SimulationConfig(seed=21, minutes=30, scenarios=("late_out_of_order",)))
        observations = [item for batch in batches for item in batch["observations"]]
        late = [item for item in observations if item["idempotency_key"].endswith("-late-arrival")]
        self.assertTrue(late)
        self.assertTrue(all(item["source_recorded_at"] < item["observed_at"] for item in late))
        self.assertEqual(len({item["idempotency_key"] for item in observations}), len(observations))

    def test_real_api_accepts_public_batches_and_flags_quality_cases(self) -> None:
        try:
            from fastapi.testclient import TestClient
            root = Path(__file__).resolve().parents[2]
            sys.path.insert(0, str(root / "services" / "api"))
            from app.config import Settings
            from app.main import create_app
        except ModuleNotFoundError as error:
            self.skipTest(f"API test dependencies unavailable: {error}")
        start = datetime.now(timezone.utc) - timedelta(minutes=4)
        configs = (
            SimulationConfig(seed=31, minutes=50, start_at=start, scenarios=("gradual_degradation", "isolated_spike", "connectivity_outage", "duplicate_replay", "unit_asset_mismatch")),
            SimulationConfig(seed=32, minutes=30, start_at=start, scenarios=("late_out_of_order",)),
        )
        with TestClient(create_app(Settings(database_url="sqlite+pysqlite:///:memory:", auto_create_schema=True))) as client:
            posted = 0
            for config in configs:
                for index, batch in enumerate(PlantGenerator(config).batches()):
                    response = client.post("/api/v1/ingestion/observations", json=batch, headers={"Idempotency-Key": f"sim-{config.seed}-{index}"})
                    self.assertEqual(response.status_code, 201, response.text)
                    posted += len(batch["observations"])
            observations, cursor = [], None
            while True:
                params = {"limit": 200, **({"cursor": cursor} if cursor else {})}
                response = client.get("/api/v1/observations", params=params).json()
                observations.extend(response["items"]); cursor = response["next_cursor"]
                if cursor is None: break
        flags = {flag for item in observations for flag in item["quality_flags"]}
        self.assertGreater(len(observations), 0)
        self.assertGreaterEqual(posted, len(observations))
        self.assertTrue({"duplicate", "invalid_unit", "late_arrival", "out_of_order"}.issubset(flags))


if __name__ == "__main__": unittest.main()
