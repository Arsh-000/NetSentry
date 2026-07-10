# NetSentry — Network Diagnostics Agent

An agentic AI system that diagnoses network device issues using a ReAct
(Reason → Act → Observe) loop, Netmiko-based tool calling, and Pydantic
schema validation — the same architecture pattern as an MCP-style tool
orchestration agent, pointed at network devices instead of business systems.

## Architecture
```
User goal ("why is Gi2 down?")
        │
        ▼
   agent.py (ReAct loop, Claude API)
        │  reasons → decides which tool to call
        ▼
   tools.py (Netmiko-backed, read-only)
        │  get_interface_status / get_config_section /
        │  get_cdp_neighbors / ping_test / propose_fix
        ▼
   Real Cisco IOS-XE device (Cisco DevNet Always-On Sandbox)
        │
        ▼
   audit_log.jsonl  ← every tool call + result logged
```

## Key design decisions (talk about these in the interview)
1. **Every diagnostic tool is read-only.** `propose_fix` never touches the
   device — it returns a structured, human-reviewable recommendation only.
   This is a deliberate human-in-the-loop guardrail, not a limitation: on a
   shared community sandbox (or any production network), an agent should
   never autonomously push config changes without approval.
2. **Pydantic schema validation on every tool input** — identical pattern to
   the HR Assist agent's tool-schema layer, reused here for a different
   domain. This is worth saying explicitly: "I reused the same guardrail
   pattern from my HR agent."
3. **Hard iteration cap (`MAX_ITERATIONS`)** prevents runaway tool-call loops.
4. **Full audit trail** (`audit_log.jsonl`) — every tool call, its inputs, and
   a preview of its result are logged, so any decision the agent made can be
   reconstructed by a human afterward.

## Setup
1. Create a free Cisco DevNet account: https://developer.cisco.com/
2. Go to https://devnetsandbox.cisco.com/RM/Topology, search "IOS XE", and
   launch the **Always-On** sandbox (no reservation/VPN needed). Copy the
   current hostname, username, and password shown in the sandbox panel
   (these rotate periodically, so always use what's currently displayed).
3. `pip install -r requirements.txt`
4. Get an xAI API key at https://console.x.ai/ (new accounts get free trial
   credit — no need to add payment for testing this project).
5. Set environment variables (never hardcode credentials):
   ```bash
   export XAI_API_KEY="your-xai-key"
   export NET_DEVICE_HOST="sandbox-iosxe-latest-1.cisco.com"
   export NET_DEVICE_USER="admin"
   export NET_DEVICE_PASS="the-current-sandbox-password"
   ```
6. **Before running against the real device**, verify the agent logic itself
   is correct with the mocked dry run:
   ```bash
   python test_dry_run.py
   ```
7. Run for real:
   ```bash
   python agent.py
   ```

## Resume bullet (use once you've run this against the real sandbox)
> **NetSentry — Network Diagnostics Agent** — Agentic AI | Network Automation | Tool Orchestration
> Built a Netmiko-based ReAct agent that autonomously diagnoses live Cisco IOS-XE interface/config issues via read-only tool calling, reusing the Pydantic schema-validation and audit-logging guardrail pattern from the HR Assist agent; all proposed fixes require explicit human approval before any device change.

## Possible extensions if you have extra time
- Add a `get_logging_buffer` tool (`show logging`) to correlate interface
  flaps with recent syslog events — closer to how a real NOC engineer works.
- Add an LLM-as-judge evaluation step: after `propose_fix`, have a second
  Claude call critique whether the diagnosis is actually supported by the
  tool outputs gathered (a mini groundedness check).
