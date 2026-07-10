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
            "description": "Get status of one or all interfaces on the device.",
            "parameters": InterfaceStatusInput.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_config_section",
            "description": "Get a filtered section of the device running-config by keyword.",
            "parameters": ConfigSectionInput.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cdp_neighbors",
            "description": "List devices directly connected to this device.",
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
            "description": "Record a proposed fix for human review. Does NOT change the device.",
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
Investigate using the available read-only tools, reason step by step,
and once you have identified a likely root cause, call propose_fix.
Never claim to have fixed anything yourself."""


def _make_client():
    return OpenAI(
        api_key=os.environ.get("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )


def run_agent(user_goal: str, device_params: dict, client=None):
    client = client or _make_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_goal},
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
    goal = "Check the status of all interfaces on this device and report any that are down or have issues."
    print(run_agent(goal, {}))