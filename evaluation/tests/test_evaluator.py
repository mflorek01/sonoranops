from __future__ import annotations

import unittest

from evaluation.evaluator import score


class EvaluationTests(unittest.TestCase):
    def test_scores_only_against_public_result_shapes(self) -> None:
        truth = {"expected_signals": [{"window": {"asset": "primary-crusher-01"}, "expected_public_signal": "anomaly", "scoring_class": "evaluation_only"}]}
        platform = {"findings": [{"finding_type": "anomaly", "asset_ref": {"asset_id": "primary-crusher-01"}}], "incidents": []}
        result = score(truth, platform)
        self.assertEqual((result.expected, result.matched, result.recall), (1, 1, 1.0))

    def test_reports_unmatched_expectations(self) -> None:
        truth = {"expected_signals": [{"window": {"asset": "screen-01"}, "expected_public_signal": "data_quality"}]}
        result = score(truth, {"findings": [], "incidents": []})
        self.assertEqual(result.matched, 0)
        self.assertEqual(result.unmatched[0]["asset"], "screen-01")


if __name__ == "__main__": unittest.main()
