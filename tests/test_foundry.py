import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from foundry.evaluation import cases, compare, run
from foundry.project import initialize, upgrade


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_init_ownership_and_upgrade(self):
        project = initialize(self.root / "one")
        with self.assertRaises(FileExistsError):
            initialize(project)
        with self.assertRaisesRegex(ValueError, "为空"):
            cases(project)
        (project / "business/system.md").write_text("custom")
        candidate = upgrade(project, self.root / "two")
        self.assertEqual((candidate / "business/system.md").read_text(), "custom")
        (project / "AGENTS.md").write_text("custom governance")
        with self.assertRaisesRegex(ValueError, "定制"):
            upgrade(project, self.root / "three")

    def test_trace_and_provenance(self):
        project = initialize(self.root / "dispatch", example=True)
        before, ok = run(project, True)
        self.assertTrue(ok)
        trace = json.loads((before / "attempt-1/agentgauge-trace.json").read_text())
        self.assertEqual(len(trace["turns"]), 2)
        self.assertTrue(any(call["name"] == "lookup_window" for call in trace["tool_calls"]))
        events = [json.loads(line) for line in (before / "attempt-1/trace.jsonl").read_text().splitlines()]
        self.assertTrue(any(e["kind"] == "tool_receipt" and "同一站点" in str(e["result"]) for e in events))
        self.assertTrue(any(e["kind"] == "model_input" and e["tools"] for e in events))
        self.assertNotIn("reported_window", json.dumps(events))
        with self.assertRaisesRegex(ValueError, "独立运行"):
            compare(before, before)
        source = project / "business/windows.json"
        source.write_text(source.read_text().replace("14:00", "13:00"))
        after, ok = run(project, True)
        self.assertFalse(ok)
        self.assertFalse(compare(before, after))
        data = json.loads((after / "run.json").read_text())
        self.assertEqual([a["status"] for a in data["attempts"]], ["fail", "pass"])
        original = (project / "evals/cases.json").read_text()
        (project / "evals/cases.json").write_text(original.replace("09:00", "08:00"))
        changed, _ = run(project, True, "shift")
        with self.assertRaisesRegex(ValueError, "不可直接比较"):
            compare(before, changed)
