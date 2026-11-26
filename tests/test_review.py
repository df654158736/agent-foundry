import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from foundry.evaluation import compare
from foundry.review import complete_run, latest, record


class ReviewTests(unittest.TestCase):
    def test_frozen_score_revisions_and_scope(self):
        with TemporaryDirectory() as location:
            base, candidate = [Path(location) / name for name in ("one", "two")]
            for root in (base, candidate):
                attempt = root / "attempt-1"
                attempt.mkdir(parents=True)
                (attempt / "delivery.json").write_text('["ready"]')
                report = {"schema": 1, "mode": "fixture", "model": "scripted", "endpoint_hash": None,
                          "eval_digest": "same", "planned": ["route"], "state": "complete",
                          "attempts": [{"case":"route", "status":"pass"}], "run":root.name}
                (root / "run.json").write_text(json.dumps(report))
            report = complete_run(candidate)
            original = (candidate / "run.json").read_bytes()
            decision = {"run":"two", "case":"route", "business":"pass", "delivery":"fail", "reviewer":"test",
                        "revision":1, "reason":"交付承诺未证实", "evidence":["delivery.json"]}
            self.assertTrue(compare(base, candidate))
            self.assertFalse(compare(base, candidate, require_review=True))
            for wrong in ({"run":"one"}, {"case":"missing"}, {"evidence":["../run.json"]}, {"evidence":["absent"]}):
                with self.assertRaises(ValueError):
                    record(candidate, report, decision | wrong)
            record(candidate, report, decision)
            self.assertFalse(compare(base, candidate, require_review=True))
            with self.assertRaises(ValueError):
                record(candidate, report, decision)
            record(candidate, report, decision | {"revision":2, "delivery":"pass", "reason":"复查权威记录后纠正原归因"})
            self.assertTrue(compare(base, candidate, require_review=True))
            (candidate / "attempt-1/delivery.json").write_text('["changed"]')
            self.assertTrue(latest(candidate, 1)["stale"])
            self.assertFalse(compare(base, candidate, require_review=True))
            self.assertEqual((candidate / "run.json").read_bytes(), original)
            self.assertTrue((candidate / "attempt-1/reviews/1.json").exists())
