"""Platform-safe wire shapes validated against the shared JSON Schema."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

FORBIDDEN_PRIVATE_TERMS = ("hidden_truth", "scenario_id", "seed", "fault_schedule", "expected_label", "ground_truth", "private_truth")
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "packages" / "contracts" / "schemas" / "observation-batch.schema.json"


def is_safe_observation(observation: dict[str, Any]) -> bool:
    serialized_keys = " ".join(_keys(observation)).lower()
    return not any(term in serialized_keys for term in FORBIDDEN_PRIVATE_TERMS)


def validate_batch(batch: dict[str, Any]) -> None:
    errors = sorted(_validator().iter_errors(batch), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(str(item) for item in first.absolute_path) or "batch"
        raise ValueError(f"shared contract schema violation at {path}: {first.message}")
    if not all(is_safe_observation(item) for item in batch["observations"]):
        raise ValueError("observation violates public contract boundary")


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [str(key) for key, nested in value.items()] + [key for nested in value.values() for key in _keys(nested)]
    if isinstance(value, list):
        return [key for nested in value for key in _keys(nested)]
    return []
