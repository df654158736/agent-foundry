"""Project a Foundry attempt into the AgentGauge 0.4.0.dev10 Trace interchange."""
def gauge_trace(session_id, case, outcome, records, started, ended):
    requests = [event for event in records if event["kind"] == "tool_request"]
    kinds = {"tool_request": "tool_call", "tool_receipt": "tool_result"}
    turns = []
    for index, prompt in enumerate(case["turns"], 1):
        stream = [event for event in records if event["turn"] == index]
        if not stream and index > len(outcome["answers"]):
            break
        turns.append({"index": index, "prompt": prompt, "events": [
            {"ts": e["time"], "kind": kinds.get(e["kind"], "raw"), "payload": e} for e in stream
        ]})
    return {
        "session_id": session_id, "target": "foundry", "case": case["id"], "attempt": 1,
        "started_at": started, "ended_at": ended, "turns": turns,
        "tool_calls": [{"name": r["tool"], "args": r["inputs"]} for r in requests if r["tool"]],
        "answer": outcome["answers"][-1] if outcome["answers"] else "",
        "terminal": {"status": "completed" if len(outcome["answers"]) == len(case["turns"]) else "incomplete"},
        "usage": {"llm_calls": sum(e["kind"] == "model_input" for e in records)},
        "timing": {"wall_ms": round(outcome["elapsed_s"] * 1000)},
    }
