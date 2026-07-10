"""
tools.py — the agent's "hands." Each function is a discrete, independently
callable tool, exactly like the MCP tools in the HR Assist agent, but pointed
at a real network device via Netmiko instead of an HR system's API.

Design decision (explain this in the interview): every tool here is READ-ONLY.
`propose_fix` never touches the device — it only returns a structured
recommendation that a human must approve before anything is applied. This
mirrors the human-in-the-loop guardrail pattern used throughout agentic AI
(and is simply good practice on a shared public sandbox device).
"""

from netmiko import ConnectHandler
from schemas import (
    InterfaceStatusInput, ConfigSectionInput, CdpNeighborsInput,
    PingTestInput, ProposeFixInput,
)
from audit_log import log_event


def _connect(device):
    return ConnectHandler(
        device_type=device.device_type,
        host=device.host,
        username=device.username,
        password=device.password,
        port=device.port,
    )


def get_interface_status(payload: InterfaceStatusInput) -> str:
    """Runs 'show ip interface brief', optionally filtered to one interface."""
    conn = _connect(payload.device)
    try:
        output = conn.send_command("show ip interface brief")
        if payload.interface:
            lines = [l for l in output.splitlines() if payload.interface in l or "Interface" in l]
            output = "\n".join(lines) if lines else f"No match found for {payload.interface}"
        log_event("get_interface_status", {"interface": payload.interface}, output[:300])
        return output
    finally:
        conn.disconnect()


def get_config_section(payload: ConfigSectionInput) -> str:
    """Runs 'show running-config | section <keyword>'."""
    conn = _connect(payload.device)
    try:
        output = conn.send_command(f"show running-config | section {payload.section_keyword}")
        log_event("get_config_section", {"section_keyword": payload.section_keyword}, output[:300])
        return output or "No matching config section found."
    finally:
        conn.disconnect()


def get_cdp_neighbors(payload: CdpNeighborsInput) -> str:
    """Runs 'show cdp neighbors' to see what's physically connected."""
    conn = _connect(payload.device)
    try:
        output = conn.send_command("show cdp neighbors")
        log_event("get_cdp_neighbors", {}, output[:300])
        return output
    finally:
        conn.disconnect()


def ping_test(payload: PingTestInput) -> str:
    """Runs a ping from the device to a target IP to test reachability."""
    conn = _connect(payload.device)
    try:
        output = conn.send_command(f"ping {payload.target_ip} repeat {payload.count}")
        log_event("ping_test", {"target_ip": payload.target_ip, "count": payload.count}, output[:300])
        return output
    finally:
        conn.disconnect()


def propose_fix(payload: ProposeFixInput) -> str:
    """
    NEVER executes anything on the device. Records a structured, human-reviewable
    recommendation. This is the guardrail checkpoint of the whole agent.
    """
    record = payload.model_dump()
    log_event("propose_fix", record, "AWAITING_HUMAN_APPROVAL")
    lines = [
        "=== PROPOSED FIX (not applied — requires human approval) ===",
        f"Device: {payload.device_host}",
        f"Interface: {payload.interface}",
        f"Diagnosis: {payload.diagnosis}",
        f"Confidence: {payload.confidence}",
        "Proposed commands:",
    ] + [f"  {c}" for c in payload.proposed_commands]
    return "\n".join(lines)
