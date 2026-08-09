# Sonoran synthetic plant simulator

This is a deterministic **data producer** for the Sonoran Operations Intelligence platform. It uses internally coherent heuristics for a small aggregate plant; it is not validated machinery physics and must not be represented as such.

## Boundaries

- `sonoran_sim` emits only `1.0` platform-safe observation envelopes.
- Scenario schedules, seeds, fault labels, and expected outcomes are written separately to `evaluation/private_truth/` by default. They are never included in a published envelope.
- The simulator can write batches to a JSONL export or POST them to the public ingestion API. It does not read platform results.
- The evaluator may read the private truth file and independently read exported platform findings/incidents (or public GET endpoints). It never posts truth to the platform.

## Run

```powershell
python -m sonoran_sim.run --seed 17 --minutes 180 --output .\output\observations.jsonl
python -m sonoran_sim.run --seed 17 --minutes 180 --api-url http://localhost:8000
python -m sonoran_sim.run --seed 17 --minutes 180 --wallclock-span-minutes 4 --anchor-end now --api-url http://localhost:8000
python -m unittest discover -s tests -v
```

`--wallclock-span-minutes` and `--anchor-end` explicitly enable demo/replay time compression. They map every simulation step across a recent span ending at an ISO-8601 timestamp or the instant captured by `now`. This changes timestamps only; it is not a plant-physics acceleration claim. The span is capped at 60 minutes, normal observations remain recent, and deliberately late/out-of-order source records retain their older source timestamps. Omit both options for the original fixed, byte-stable timeline.

The default run covers normal operation plus configurable scenario families: crusher degradation, isolated spike, frozen/drifting sensors, connectivity outage, screen restriction, planned maintenance, duplicate/replay, late/out-of-order arrival, unit/asset mismatch, schema drift, and demand/order risk. Restrict a run with `--scenarios gradual_degradation,connectivity_outage`.

The topology is feeder → primary crusher → secondary crusher → screen → conveyors/stacker → stockpiles. It also produces synthetic production, quality, maintenance, and dispatch records. The relationships (for example, restricted screen capacity raising crusher load and reducing production) are documented heuristics.

`unit_asset_mismatch` deliberately emits two distinct public cases: a known metric with an invalid unit, and an `unmapped-sensor-01` identifier. The current API detects the invalid unit but does not yet have an asset-type registry to classify the unknown/mismatched identifier; it remains accepted platform-visible source data for future data-quality capability.
