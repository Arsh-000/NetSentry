"""
agent.py — the ReAct loop: Reason -> Act (tool call) -> Observe -> repeat.

Uses Groq API via the OpenAI-compatible client.

Guardrails implemented here:
  1. MAX_ITERATIONS — hard stop, prevents infinite tool-call loops.
  2. Schema validation on every tool input via Pydantic (schemas.py).
  3. propose_fix never mutates the device — see tools.py docstring.
  4. Every tool call is written to audit_log.jsonl (traceability).
"""

import json
import os
from openai import OpenAI
from schemas import (
    InterfaceStatusInput, ConfigSectionInput, CdpNeighborsInput,
    PingTestInput, ProposeFixInput,
)
from tools import (
    get_interface_status, get_config_section, get_cdp_neighbors,
    ping_test, propose_fix,
)

MAX_ITERATIONS = 8
MODEL = "llama-3.3-70b-versatile"

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "get_interface_status",
            "description": "Get status (up/down, IP, protocol) of one or all interfaces on a device.",
            "parameters": InterfaceStatusInput.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_config_section",
            "description": "Get a filtered section of the device's running configuration by keyword.",
            "parameters": ConfigSectionInput.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cdp_neighbors",
            "description": "List devices directly connected to this device (CDP neighbors).",
            "parameters": CdpNeighborsInput.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ping_test",
            "description": "Ping a target IP from the device to test reachability.",
            "parameters": PingTestInput.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_fix",
            "description": (
                "Record a proposed fix for human review. Does NOT change the device. "
                "Call this once you've diagnosed the issue and are ready to recommend action."
            ),
            "parameters": ProposeFixInput.model_json_schema(),
        },
    },
]

TOOL_IMPL = {
    "get_interface_status": (get_interface_status, InterfaceStatusInput),
    "get_config_section": (get_config_section, ConfigSectionInput),
    "get_cdp_neighbors": (get_cdp_neighbors, CdpNeighborsInput),
    "ping_test": (ping_test, PingTestInput),
    "propose_fix": (propose_fix, ProposeFixInput),
}

SYSTEM_PROMPT = """You are NetSentry, a network diagnostics agent.
Given a symptom (e.g. "interface Gi2 is down"), investigate using the
available read-only tools, reason step by step, and once you've identified
a likely root cause, call propose_fix with your diagnosis and exact CLI
commands you'd recommend. Never claim to have fixed anything yourself —
you only diagnose and propose; a human applies the fix."""


def _make_client():
    return OpenAI(
        api_key=os.environ.get("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )


def run_agent(user_goal: str, device_params: dict, client=None):
    client = client or _make_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{user_goal}\n\nDevice params: {json.dumps(device_params)}"},
    ]

    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SPECS,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True) if hasattr(message, "model_dump") else message)

        if not getattr(message, "tool_calls", None):
            return message.content

        for call in message.tool_calls:
            fn, schema_cls = TOOL_IMPL[call.function.name]
            try:
                args = json.loads(call.function.arguments)
                validated = schema_cls(**args)
                result = fn(validated)
            except Exception as e:
                result = f"TOOL ERROR: {e}"
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })

    return "Max iterations reached without a final diagnosis."


if __name__ == "__main__":
    device = {
        "host": os.environ.get("NET_DEVICE_HOST", "devnetsandboxiosxec8k.cisco.com"),
        "username": os.environ.get("NET_DEVICE_USER", "jokearns"),
        "password": os.environ.get("NET_DEVICE_PASS", "CHANGE_ME"),
        "device_type": "cisco_xe",
        "port": 22,
    }
    goal = "Investigate why GigabitEthernet2 might be having issues and propose a fix if you find one."
    print(run_agent(goal, device))