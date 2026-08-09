from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validate

CONTRACTS = Path(__file__).resolve().parents[3] / "packages" / "contracts"


def load_json(relative_path: str) -> dict:
    return json.loads((CONTRACTS / relative_path).read_text(encoding="utf-8"))


def test_observation_contract_accepts_public_fixture_and_rejects_malformed_fixture() -> None:
    schema = load_json("schemas/observation-batch.schema.json")
    Draft202012Validator.check_schema(schema)
    validate(load_json("fixtures/observation-batch.valid.json"), schema)

    with pytest.raises(ValidationError):
        validate(load_json("fixtures/observation-batch.malformed.json"), schema)
