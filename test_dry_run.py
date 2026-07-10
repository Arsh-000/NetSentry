"""
test_dry_run.py — validates agent.py's control flow WITHOUT needing a real
xAI API key or a real network device. Mocks both. Run this first to confirm
the loop, schema validation, and tool dispatch all work correctly.
"""

import sys
import json
from unittest.mock import patch

sys.path.insert(0, ".")

import agent  # noqa: E402


class FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments  # must be a JSON string, matching real API behavior


class FakeToolCall:
    def __init__(self, id_, name, arguments_dict):
        self.id = id_
        self.function = FakeFunction(name, json.dumps(arguments_dict))


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, exclude_none=True):
        d = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in self.tool_calls
            ]
        return d


class FakeChoice:
    def __init__(self, message):
        self.message = message


class FakeResponse:
    def __init__(self, message):
        self.choices = [FakeChoice(message)]


class FakeCompletions:
    def __init__(self):
        self.call_count = 0

    def create(self, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            tool_call = FakeToolCall(
                "call_1", "get_interface_status",
                {"device": {"host": "sandbox", "username": "admin",
                            "password": "x", "device_type": "cisco_ios"},
                 "interface": "GigabitEthernet2"},
            )
            return FakeResponse(FakeMessage(content=None, tool_calls=[tool_call]))
        elif self.call_count == 2:
            tool_call = FakeToolCall(
                "call_2", "propose_fix",
                {
                    "device_host": "sandbox", "interface": "GigabitEthernet2",
                    "diagnosis": "Interface administratively down",
                    "proposed_commands": ["interface GigabitEthernet2", "no shutdown"],
                    "confidence": "high",
                },
            )
            return FakeResponse(FakeMessage(content=None, tool_calls=[tool_call]))
        else:
            return FakeResponse(FakeMessage(content="Diagnosis complete. Fix proposed and logged for human review."))


class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self):
        self.chat = FakeChat()


def fake_get_interface_status(payload):
    return "GigabitEthernet2 is administratively down, line protocol down"


def main():
    with patch.dict(agent.TOOL_IMPL, {
        "get_interface_status": (fake_get_interface_status, agent.InterfaceStatusInput),
    }):
        result = agent.run_agent(
            "Investigate GigabitEthernet2",
            {"host": "sandbox", "username": "admin", "password": "x", "device_type": "cisco_ios"},
            client=FakeClient(),
        )
        print("FINAL AGENT OUTPUT:\n", result)
        assert "Diagnosis complete" in result
        print("\n✅ Dry run passed: loop, schema validation, and tool dispatch all work correctly with the Grok/OpenAI-style API format.")


if __name__ == "__main__":
    main()
