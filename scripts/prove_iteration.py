"""Reproducible fault-injection and candidate comparison in disposable projects."""
import argparse
import json
from pathlib import Path
import tempfile

from foundry.evaluation import compare, run
from foundry.project import initialize


def demonstrate(destination):
    baseline = initialize(destination / "baseline", example=True)
    candidate = initialize(destination / "candidate", example=True)
    tool = baseline / "business/tools.py"
    correct = '(row["station"], row["day"]) == (station, day)'
    source = tool.read_text()
    if source.count(correct) != 1:
        raise ValueError("示例已变更，请重新核对故障注入位置")
    tool.write_text(source.replace(correct, 'row["station"] == station'))
    before, old_passed = run(baseline, True)
    after, new_passed = run(candidate, True)
    attempts = json.loads((before / "run.json").read_text())["attempts"]
    statuses = {attempt["case"]: attempt["status"] for attempt in attempts}
    failed_checks = {
        (attempt["case"], name) for attempt in attempts
        for name, passed in attempt.get("checks", {}).items() if not passed
    }
    if statuses != {"shift": "fail", "missing": "pass"} or failed_checks != {
        ("shift", "turn2.source_and_scope"), ("shift", "turn2.reported_window"),
    }:
        raise RuntimeError(f"原样例应仅在改期轮次违约：{statuses} {failed_checks}")
    if old_passed or not new_passed or not compare(before, after):
        raise RuntimeError("受控反例未得到期望结果")
    print(f"冻结基线 {before}\n修复候选 {after}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    directory = args.out or Path(tempfile.mkdtemp(prefix="foundry-proof-"))
    directory.mkdir(parents=True, exist_ok=True)
    demonstrate(directory)
