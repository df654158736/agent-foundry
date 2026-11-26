"""Append-only attempts over the same Session used for chat."""
import hashlib
import json
import os
from pathlib import Path
import platform
import traceback
from threading import Lock
from time import monotonic, time
from uuid import uuid4

from langchain_core.callbacks import BaseCallbackHandler

from . import __version__
from .gauge import gauge_trace
from .privacy import scrub
from .project import digest_files, extension
from .runtime import Session, live_model
from .review import accepted, latest, summary


def save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(scrub(value), ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


class Recorder(BaseCallbackHandler):
    """Record only conversation and tool data, never HTTP headers or model configuration."""
    raise_error = True

    def __init__(self, folder):
        self.path = folder / "trace.jsonl"
        self.events = []
        self.lock = Lock()
        self.turn = 0

    def add(self, kind, run_id, **payload):
        event = {"kind": kind, "call": str(run_id), "time": time(), "turn": self.turn, **payload}
        with self.lock:
            event = scrub(event)
            line = json.dumps(event, ensure_ascii=False)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
            self.events.append(event)

    def on_chat_model_start(self, serialized, messages, *, run_id, invocation_params=None, **kwargs):
        for batch in messages:
            self.add("model_input", run_id, messages=[{
                "role": m.type, "content": m.content, "tool_calls": getattr(m, "tool_calls", []),
                "tool_call_id": getattr(m, "tool_call_id", None),
            } for m in batch], tools=(invocation_params or {}).get("tools", []))

    def on_llm_end(self, response, *, run_id, **kwargs):
        for group in response.generations:
            for generation in group:
                msg = getattr(generation, "message", None)
                if msg is not None:
                    self.add("model_output", run_id, content=msg.content, proposals=getattr(msg, "tool_calls", []))

    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        self.add("tool_request", run_id, tool=(serialized or {}).get("name"), arguments=input_str,
                 inputs=kwargs.get("inputs") or {})

    def on_tool_end(self, output, *, run_id, **kwargs):
        self.add("tool_receipt", run_id, tool=getattr(output, "name", None),
                 result=getattr(output, "content", str(output)), status=getattr(output, "status", None))

    def on_tool_error(self, error, *, run_id, **kwargs):
        self.add("tool_error", run_id, error_type=type(error).__name__)


def cases(root):
    items = json.loads((root / "evals/cases.json").read_text())
    if not isinstance(items, list) or not items:
        raise ValueError("场景集为空，请先补充 evals/cases.json")
    seen = set()
    for case in items:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"].strip():
            raise ValueError("用例缺少 id")
        if case["id"] in seen:
            raise ValueError("用例 id 重复")
        seen.add(case["id"])
        if not isinstance(case.get("turns"), list) or not case["turns"] or not all(
            isinstance(turn, str) and turn.strip() for turn in case["turns"]
        ):
            raise ValueError("每个用例需要非空 turns")
    return items


def run(root, fixture, case_id=None, output=None):
    items = cases(root)
    if case_id:
        items = [case for case in items if case["id"] == case_id]
        if not items:
            raise ValueError(f"用例不存在 {case_id}")
    folder = (output or root / ".runs") / uuid4().hex
    folder.mkdir(parents=True, mode=0o700)
    report = {
        "schema": 1, "run": folder.name, "kit_version": __version__, "python": platform.python_version(),
        "mode": "fixture" if fixture else "live",
        "model": "scripted" if fixture else os.getenv("FOUNDRY_MODEL"),
        "endpoint_hash": None if fixture else hashlib.sha256(os.getenv("OPENAI_BASE_URL", "default").encode()).hexdigest(),
        "business_digest": digest_files(root, (root / "business").rglob("*")),
        "eval_digest": digest_files(root, (root / "evals").rglob("*")),
        "runtime_digest": digest_files(Path(__file__).parent, Path(__file__).parent.glob("*.py")),
        "lock_digest": hashlib.sha256((Path(__file__).resolve().parents[1] / "uv.lock").read_bytes()).hexdigest(),
        "planned": [case["id"] for case in items], "attempts": [], "state": "running",
    }
    save(folder / "run.json", report)
    for number, case in enumerate(items, 1):
        attempt = folder / f"attempt-{number}"
        attempt.mkdir()
        save(attempt / "case.json", case)
        recorder = Recorder(attempt)
        answers = []
        outcome = {"case": case["id"], "attempt": attempt.name, "answers": answers}
        wall_start = time()
        session_id = f"{folder.name}-{number}"
        started = monotonic()
        try:
            if fixture:
                model = extension(root / "evals/simulation.py").make_model()
            else:
                model = live_model()
            session = Session(root, model, [recorder])
            session_id = session.config["configurable"]["thread_id"]
            for recorder.turn, prompt in enumerate(case["turns"], 1):
                answers.append(session.ask(prompt))
                save(attempt / "delivery.json", answers)
            checks = extension(root / "evals/oracle.py").assess(case, answers, recorder.events)
            if not isinstance(checks, dict) or not checks or any(type(v) is not bool for v in checks.values()):
                raise ValueError("Oracle 需要返回非空的布尔检查项字典")
            outcome.update(checks=checks, status="pass" if all(checks.values()) else "fail")
        except Exception as exc:
            frame = traceback.extract_tb(exc.__traceback__)[-1]
            outcome.update(status="error", error_type=type(exc).__name__,
                           location=f"{Path(frame.filename).name}:{frame.lineno} ({frame.name})")
            print(f"{case['id']} 未完成 ({type(exc).__name__})，请检查模型配置、工具或 Oracle。")
        outcome["elapsed_s"] = round(monotonic() - started, 3)
        save(attempt / "agentgauge-trace.json", gauge_trace(
            session_id, case, outcome, recorder.events, wall_start, time()))
        report["attempts"].append(outcome)
        save(folder / "run.json", report)
    report["state"] = "complete"
    save(folder / "run.json", report)
    return folder, all(a["status"] == "pass" for a in report["attempts"])


def compare(baseline, candidate, *, require_review=False):
    left, right = [json.loads((path / "run.json").read_text()) for path in (baseline, candidate)]
    if left["run"] == right["run"]:
        raise ValueError("需要两个独立运行")
    keys = ("schema", "mode", "model", "endpoint_hash", "eval_digest", "planned")
    changed = [key for key in keys if left[key] != right[key]]
    if changed or any(batch["state"] != "complete" for batch in (left, right)):
        raise ValueError("运行不可直接比较，请核对完整性和冻结条件 " + ", ".join(changed))
    for batch in (left, right):
        if not batch["planned"] or [a["case"] for a in batch["attempts"]] != batch["planned"]:
            raise ValueError("运行分母不完整")
    print(f"{left['mode']} · {left['run']} → {right['run']}")
    reviewed = True
    for index, (a, b) in enumerate(zip(left["attempts"], right["attempts"], strict=True), 1):
        old, new = latest(baseline, index), latest(candidate, index)
        reviewed &= accepted(new)
        print(f"{a['case']}: {a['status']} → {b['status']} · {summary(old)} → {summary(new)}")
    return all(a["status"] == "pass" for a in right["attempts"]) and (reviewed or not require_review)
