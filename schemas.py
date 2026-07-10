"""
schemas.py — Pydantic input validation for every NetSentry tool.

Same pattern used in the HR Assist agent: every tool gets a strict schema
so malformed LLM tool-calls fail loudly and early instead of silently
hitting the network device with garbage input.
"""

from pydantic import BaseModel, Field
from typing import Optional


class DeviceParams(BaseModel):
    """Connection details for the target network device."""
    host: str = Field(..., description="Device hostname or IP, e.g. sandbox-iosxe-latest-1.cisco.com")
    username: str = Field(..., description="SSH username")
    password: str = Field(..., description="SSH password")
    device_type: str = Field(default="cisco_ios", description="Netmiko device_type string")
    port: int = Field(default=22)


class InterfaceStatusInput(BaseModel):
    device: DeviceParams
    interface: Optional[str] = Field(
        default=None,
        description="Specific interface to inspect, e.g. GigabitEthernet1. If omitted, returns all interfaces."
    )


class ConfigSectionInput(BaseModel):
    device: DeviceParams
    section_keyword: str = Field(..., description="Keyword to filter running-config, e.g. 'interface' or 'ospf'")


class CdpNeighborsInput(BaseModel):
    device: DeviceParams


class PingTestInput(BaseModel):
    device: DeviceParams
    target_ip: str = Field(..., description="IP address to ping from the device")
    count: int = Field(default=5, ge=1, le=20)


class ProposeFixInput(BaseModel):
    device_host: str
    interface: str
    diagnosis: str = Field(..., description="Root cause the agent believes it found")
    proposed_commands: list[str] = Field(..., description="Exact CLI commands the agent would run to fix it")
    confidence: str = Field(..., description="low | medium | high")
