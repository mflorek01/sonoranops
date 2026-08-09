from __future__ import annotations

import argparse
from pathlib import Path

from .generator import DEFAULT_SCENARIOS, PlantGenerator, SimulationConfig
from .publisher import ApiPublisher, JsonlPublisher


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit deterministic, platform-safe synthetic observation batches.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--minutes", type=int, default=180)
    parser.add_argument("--output", type=Path, default=Path("output/observations.jsonl"))
    parser.add_argument("--truth-output", type=Path, default=Path("../evaluation/private_truth/scenario_truth.json"))
    parser.add_argument("--api-url", help="Optional public API base URL; never receives truth.")
    parser.add_argument("--scenarios", default=",".join(DEFAULT_SCENARIOS), help="Comma-separated scenario families.")
    parser.add_argument("--wallclock-span-minutes", type=float, help="Compress all simulation steps into this recent wall-clock span (maximum 60 minutes).")
    parser.add_argument("--anchor-end", help="Required with --wallclock-span-minutes: ISO-8601 end timestamp or 'now'.")
    args = parser.parse_args()
    scenarios = tuple(item.strip() for item in args.scenarios.split(",") if item.strip())
    unknown = set(scenarios).difference(DEFAULT_SCENARIOS)
    if unknown: parser.error(f"Unknown scenarios: {', '.join(sorted(unknown))}")
    if (args.wallclock_span_minutes is None) != (args.anchor_end is None):
        parser.error("--wallclock-span-minutes and --anchor-end must be provided together")
    generator = PlantGenerator(SimulationConfig(
        seed=args.seed,
        minutes=args.minutes,
        scenarios=scenarios,
        wallclock_span_minutes=args.wallclock_span_minutes,
        anchor_end=args.anchor_end,
    ))
    publisher = ApiPublisher(args.api_url) if args.api_url else JsonlPublisher(args.output)
    count = 0
    for batch in generator.batches():
        publisher.publish(batch); count += len(batch["observations"])
    generator.write_truth(args.truth_output)
    print(f"Published {count} public observations in deterministic batches.")
    print(f"Private evaluator truth written to {args.truth_output} (not published).")


if __name__ == "__main__":
    main()
