"""Independent reference: synthetic approved schedule in cases.json, never sent to the agent."""
import json
import re


def assess(case, answers, events):
    checks = {}
    for turn, (answer, expected) in enumerate(zip(answers, case["expected"], strict=True), 1):
        receipts = [
            json.loads(e["result"]) for e in events if e["turn"] <= turn and e["kind"] == "tool_receipt"
            and e["tool"] == "lookup_window" and e["status"] == "success"
        ]
        expected_status = "published" if expected else "unpublished"
        checks[f"turn{turn}.source_and_scope"] = any(
            row.get("station") == case["station"] and row.get("day") == case["dates"][turn - 1]
            and row.get("status") == expected_status for row in receipts
        )
        times = re.findall(r"(?<!\d)(?:[01]?\d|2[0-3]):[0-5]\d(?!\d)", answer)
        if expected:
            checks[f"turn{turn}.reported_window"] = [t.zfill(5) for t in times] == expected
        else:
            checks[f"turn{turn}.no_invented_window"] = not times
    return checks
