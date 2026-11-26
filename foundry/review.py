"""Case-level adjudications beside the frozen run, kept across reviewer revisions."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from .privacy import scrub

VERDICTS = ("pass", "fail", "blocked", "unverified")


def complete_run(folder):
    report = json.loads((folder / "run.json").read_text())
    attempts = report["attempts"]
    if (report["state"] != "complete" or not report["planned"]
            or report["planned"] != [item["case"] for item in attempts]):
        raise ValueError("复核需要完整运行及原分母")
    return report


def latest(folder, index):
    directory = folder / f"attempt-{index}" / "reviews"
    revisions = sorted(directory.glob("[0-9]*.json"), key=lambda path: int(path.stem))
    if not revisions:
        return None
    decision = json.loads(revisions[-1].read_text())
    for name, digest in decision["evidence_sha256"].items():
        path = directory.parent / name
        if not path.is_file() or evidence_hash(path) != digest:
            decision["stale"] = True
            break
    return decision


def evidence_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def record(folder, report, decision):
    if decision.get("run") != report["run"] or decision.get("case") not in report["planned"]:
        raise ValueError("复核记录与原运行或用例不符")
    index = report["planned"].index(decision["case"]) + 1
    attempt = folder / f"attempt-{index}"
    for field in ("reviewer", "reason"):
        if not isinstance(decision.get(field), str) or not decision[field].strip():
            raise ValueError(f"缺少 {field}")
    for field in ("business", "delivery"):
        if decision.get(field) not in VERDICTS:
            raise ValueError(f"{field} 需要明确裁定")
    evidence = decision.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("需要本次尝试的证据引用")
    hashes = {}
    for item in evidence:
        if not isinstance(item, str) or Path(item).is_absolute():
            raise ValueError("证据必须引用本次尝试中的相对路径")
        path = (attempt / item).resolve()
        if not path.is_relative_to(attempt.resolve()) or not path.is_file():
            raise ValueError("证据文件不存在或不属于本次尝试")
        hashes[item] = evidence_hash(path)
    previous = latest(folder, index)
    revision = previous["revision"] + 1 if previous else 1
    if type(decision.get("revision")) is not int or decision["revision"] != revision:
        raise ValueError(f"请核对已有意见后追加第 {revision} 版")
    directory = attempt / "reviews"
    directory.mkdir(exist_ok=True)
    fields = ("revision", "run", "case", "business", "delivery", "reviewer", "reason", "evidence")
    data = scrub({k: decision[k] for k in fields})
    data["evidence_sha256"] = hashes
    with NamedTemporaryFile(dir=directory, mode="w", encoding="utf-8", delete=False) as temp:
        try:
            json.dump(data, temp, ensure_ascii=False, indent=2)
            temp.flush()
            os.link(temp.name, directory / f"{revision}.json")
        finally:
            Path(temp.name).unlink(missing_ok=True)


def summary(decision):
    if decision is None:
        return "待复核"
    if decision.get("stale"):
        return f"证据已变更，待复核 (r{decision['revision']})"
    return f"业务 {decision['business']} / 正文 {decision['delivery']} (r{decision['revision']})"


def accepted(decision):
    return decision is not None and not decision.get("stale") and decision["business"] == decision["delivery"] == "pass"


def show(folder, decision_file=None):
    report = complete_run(folder)
    if decision_file:
        decision = json.loads(decision_file.read_text())
        if not isinstance(decision, dict):
            raise ValueError("每份输入对应一个用例的复核记录")
        record(folder, report, decision)
    print(f"{report['mode']} · {report['run']}")
    for index, item in enumerate(report["attempts"], 1):
        decision = latest(folder, index)
        attempt = folder / f"attempt-{index}"
        print(f"{item['case']} · 自动 {item['status']} · {summary(decision)} · {attempt}")
        if decision:
            print(f"  {decision['reviewer']} · {decision['reason']}")
            print("  " + ", ".join(decision['evidence']))
