# NetSentry — Agentic Network Diagnostics Tool

NetSentry is an AI-powered network diagnostics agent that autonomously investigates network device issues using a ReAct (Reason → Act → Observe) loop, Netmiko-based tool calling, Pydantic schema validation, and human-approved fix proposals.

## What it does
You give it a goal like *"check all interfaces and report any issues"* — it SSHs into the real device, runs diagnostic commands, reasons over what it finds, and proposes a fix. It never applies the fix automatically — a human must approve every change before anything is executed on the device.

## Architecture
```
User goal ("check all interfaces")
        │
        ▼
   agent.py (ReAct loop — Groq llama-3.3-70b-versatile)
        │  reasons → decides which tool to call
        ▼
   tools.py (Netmiko-backed, read-only tools)
        │  get_interface_status / get_config_section /
        │  get_cdp_neighbors / ping_test / propose_fix
        ▼
   Real Cisco IOS-XE device (Cisco DevNet Always-On Sandbox)
        │
        ▼
   audit_log.jsonl  ← every tool call + result logged
```

## Key Design Decisions
1. **Every diagnostic tool is read-only.** `propose_fix` never touches the device — it only records a structured, human-reviewable recommendation.
2. **Flat Pydantic schemas on every tool input** — device credentials are read from environment variables, not passed through the LLM, avoiding complex nested schemas that some providers reject.
3. **Hard iteration cap (MAX_ITERATIONS = 8)** — prevents runaway tool-call loops.
4. **Full audit trail** (`audit_log.jsonl`) — every tool call, its inputs, and result preview are logged for traceability.

## Tech Stack
- Python 3.10+
- [Groq API](https://console.groq.com) (llama-3.3-70b-versatile) via OpenAI-compatible client
- [Netmiko](https://github.com/ktbyers/netmiko) for SSH-based CLI automation
- [Pydantic](https://docs.pydantic.dev/) for tool input validation
- [Cisco DevNet Always-On Sandbox](https://devnetsandbox.cisco.com) for live device testing

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get a free Groq API key
Sign up at [console.groq.com](https://console.groq.com) — free, no credit card required.

### 3. Get a free Cisco DevNet sandbox
1. Go to [devnetsandbox.cisco.com](https://devnetsandbox.cisco.com)
2. Search for **"Catalyst 8000 Always-On"**
3. Click Launch — credentials (host, username, password) are shown in the Instructions tab

### 4. Set environment variables
```bash
# Windows PowerShell
$env:GROQ_API_KEY="your-groq-key"
$env:NET_DEVICE_HOST="devnetsandboxiosxec8k.cisco.com"
$env:NET_DEVICE_USER="your-sandbox-username"
$env:NET_DEVICE_PASS="your-sandbox-password"

# Mac/Linux
export GROQ_API_KEY="your-groq-key"
export NET_DEVICE_HOST="devnetsandboxiosxec8k.cisco.com"
export NET_DEVICE_USER="your-sandbox-username"
export NET_DEVICE_PASS="your-sandbox-password"
```

### 5. Run the offline dry-run first (no API key or device needed)
```bash
python test_dry_run.py
```
Expected output:
```
✅ Dry run passed: loop, schema validation, and tool dispatch all work correctly.
```

### 6. Run for real
```bash
python agent.py
```

## Project Structure
```
netsentry/
├── agent.py          # ReAct loop — the main agent orchestrator
├── tools.py          # Netmiko-backed tool functions (all read-only)
├── schemas.py        # Pydantic input schemas for every tool
├── audit_log.py      # JSONL audit logger
├── test_dry_run.py   # Offline test — validates full loop without API or device
├── requirements.txt
└── README.md
```

## How the ReAct Loop Works
```
1. User gives a goal → agent receives it
2. Agent reasons: "I should check interface status first"
3. Agent calls get_interface_status tool → gets real device output
4. Agent reasons over result: "GigabitEthernet2 is down"
5. Agent calls propose_fix → logs recommendation for human review
6. Agent gives final plain-English summary
```

## Guardrails
- `propose_fix` is the only "action" tool — it never executes anything
- Every tool call is validated against a Pydantic schema before execution
- MAX_ITERATIONS hard cap prevents infinite loops
- All decisions logged to `audit_log.jsonl` for full auditability


- "Tool credentials are read from environment variables, not passed through the LLM — a deliberate security decision"
- "The dry-run test harness mocks both the LLM and the device, so the agent logic can be validated without any external dependency"
- "propose_fix is a human-in-the-loop guardrail — the agent diagnoses and proposes, a human approves before any real change"
