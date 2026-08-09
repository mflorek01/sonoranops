# Evaluation harness

The evaluator scores **after** a platform run. It reads evaluator-only truth from `evaluation/private_truth/` and either:

1. reads a platform export containing `findings` and `incidents`, or
2. performs public `GET /api/v1/findings` and `GET /api/v1/incidents` requests.

It never calls ingestion, does not expose truth in a request, and has no import from `simulator` runtime code.

```powershell
python -m evaluation.run --truth .\private_truth\scenario_truth.json --platform-export .\platform-results.json
python -m evaluation.run --truth .\private_truth\scenario_truth.json --api-url http://localhost:8000
python -m unittest discover -s tests -v
```

The score is intentionally coarse until API finding schemas/asset associations are finalized: it reports expected classes and whether public findings/incidents contain matching `finding_type`/asset evidence. It is a regression aid, not a model-validation claim.

The current API has ingestion-quality rules for duplicate and invalid-unit data, but no anomaly detector for the process scenarios and no asset-type registry for unknown identifiers. Treat unmatched degradation, outage, restriction, and demand scenarios as capability gaps—not failed machinery-physics validation.
