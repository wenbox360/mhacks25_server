# tools.py
from fastmcp import FastMCP, Context
from typing import Dict, Any
from sendQueue import add_command_to_queue

# --- Tool implementations (not decorated) ---

async def piezo_beep_impl(context: Context, duration: int = 500) -> Dict[str, Any]:
    """Control piezo buzzer - duration in milliseconds."""
    if duration <= 0:
        return {"error": "duration must be > 0"}
    command = {"command": 2, "value": duration}
    add_command_to_queue(command)
    return {"message": f"Sent beep for {duration}ms"}


async def control_servo_impl(context: Context, position: int) -> Dict[str, Any]:
    """Control servo motor position - position in degrees (0-180)."""
    if not 0 <= position <= 180:
        return {"error": "Position must be between 0 and 180 degrees"}
    servo_command_id = 20
    command = {"command": servo_command_id, "value": position}
    add_command_to_queue(command)
    return {"message": f"Servo set to {position} degrees", "position": position}


# --- Registry of all tools with their hardware dependency ---
TOOL_SPECS = [
    {"name": "piezo_beep", "impl": piezo_beep_impl, "hardware": "Piezo Buzzer"},
    {"name": "control_servo", "impl": control_servo_impl, "hardware": "Micro Servo - SG90"},
]


# --- Registration function ---

def register_tools(mcp: FastMCP, available_hardware: set[str]):
    """Enable/disable tools based on available_hardware."""
    for spec in TOOL_SPECS:
        enabled = spec["hardware"] in available_hardware
        if enabled:
            mcp.tool(enabled=enabled)(spec["impl"])
            print(f"Registered {spec['name']} enabled={enabled}")
