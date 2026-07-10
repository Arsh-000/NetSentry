"""audit_log.py — every tool call gets logged, so any decision the agent
makes can be reconstructed by a human afterward (traceability guardrail)."""

import json
import datetime
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), "audit_log.jsonl")


def log_event(tool_name: str, inputs: dict, result_preview: str):
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "tool": tool_name,
        "inputs": inputs,
        "result_preview": str(result_preview)[:300],
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
