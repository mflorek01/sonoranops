from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluator import load_export, read_public_api, score


def main() -> None:
    parser = argparse.ArgumentParser(description="Score public platform results against evaluator-only truth.")
    parser.add_argument("--truth", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--platform-export", type=Path)
    source.add_argument("--api-url")
    args = parser.parse_args()
    truth = load_export(args.truth)
    platform = read_public_api(args.api_url) if args.api_url else load_export(args.platform_export)
    result = score(truth, platform)
    print(json.dumps({"expected": result.expected, "matched": result.matched, "recall": round(result.recall, 3), "unmatched": result.unmatched}, indent=2))


if __name__ == "__main__": main()
