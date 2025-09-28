# tools.py
from fastmcp import FastMCP, Context
from typing import Dict, Any
from sendQueue import add_command_to_queue, responses
import asyncio
import uuid

# --- Tool implementations (not decorated) ---


async def piezo_beep_impl(context, duration: int = 500):
    if duration <= 0:
        return {"error": "duration must be > 0"}
    response_key = f"beep_{uuid.uuid4().hex[:8]}"
    command = {"command": 2, "value": duration, "response_key": response_key}
    add_command_to_queue(command)

    timeout = 3.0
    start = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start) < timeout:
        resp = responses.get(response_key)
        if resp is not None:
            return {"message": f"Sent beep for {duration}ms", "response": resp}
        await asyncio.sleep(0.05)

    return {"message": f"Sent beep for {duration}ms", "response": None, "warning": "no response from Arduino (timeout)"}


async def control_servo_impl(context: Context, position: int) -> Dict[str, Any]:
    """Control servo motor position - position in degrees (0-180)."""
    if not 0 <= position <= 180:
        return {"error": "Position must be between 0 and 180 degrees"}
    servo_command_id = 20
    command = {"command": servo_command_id, "value": position}
    add_command_to_queue(command)
    return {"message": f"Servo set to {position} degrees", "position": position}


# --- Tool implementations for all hardware types ---

async def read_temperature_impl(context: Context, pin: int) -> Dict[str, Any]:
    """Read temperature from DHT22 sensor on specified pin."""
    command = {"command": 10, "pin": pin}
    add_command_to_queue(command)
    return {"message": f"Reading temperature from DHT22 on pin {pin}", "sensor": "DHT22", "pin": pin}

async def read_humidity_impl(context: Context, pin: int) -> Dict[str, Any]:
    """Read humidity from DHT22 sensor on specified pin."""
    command = {"command": 14, "pin": pin}
    add_command_to_queue(command)
    return {"message": f"Reading humidity from DHT22 on pin {pin}", "sensor": "DHT22", "pin": pin}

async def control_led_impl(context: Context, pin: int, state: str) -> Dict[str, Any]:
    """Control LED on specified pin - state should be 'on' or 'off'."""
    if state.lower() not in ['on', 'off']:
        return {"error": "State must be 'on' or 'off'"}
    value = 1 if state.lower() == 'on' else 0
    command = {"command": 16, "pin": pin, "value": value}
    add_command_to_queue(command)
    return {"message": f"LED turned {state} on pin {pin}", "state": state, "pin": pin}

async def control_relay_impl(context: Context, pin: int, state: str) -> Dict[str, Any]:
    """Control relay on specified pin - state should be 'on' or 'off'."""
    if state.lower() not in ['on', 'off']:
        return {"error": "State must be 'on' or 'off'"}
    value = 1 if state.lower() == 'on' else 0
    command = {"command": 15, "pin": pin, "value": value}
    add_command_to_queue(command)
    return {"message": f"Relay {state} on pin {pin}", "state": state, "pin": pin}

async def read_button_impl(context: Context, pin: int) -> Dict[str, Any]:
    """Read button state on specified pin."""
    command = {"command": 13, "pin": pin}
    add_command_to_queue(command)
    return {"message": f"Reading button state on pin {pin}", "pin": pin}

async def read_distance_ultrasonic_impl(context: Context, trigger_pin: int, echo_pin: int) -> Dict[str, Any]:
    """Read distance from HC-SR04 ultrasonic sensor."""
    command = {"command": 11, "trigger_pin": trigger_pin, "echo_pin": echo_pin}
    add_command_to_queue(command)
    return {"message": f"Reading distance from HC-SR04: trigger pin {trigger_pin}, echo pin {echo_pin}", "trigger_pin": trigger_pin, "echo_pin": echo_pin, "sensor": "HC-SR04"}

async def read_distance_ir_impl(context: Context, pin: int) -> Dict[str, Any]:
    """Read distance from IR distance sensor."""
    command = {"command": 12, "pin": pin}
    add_command_to_queue(command)
    return {"message": f"Reading distance from IR sensor on pin {pin}", "sensor": "IR Distance Sensor", "pin": pin}

# --- Registry of all tools with their hardware dependency ---
TOOL_SPECS = [
    {"name": "piezo_beep", "impl": piezo_beep_impl, "hardware": "Piezo_Buzzer"},
    {"name": "control_servo", "impl": control_servo_impl, "hardware": "Micro_Servo_SG90"},
    {"name": "read_temperature", "impl": read_temperature_impl, "hardware": "dht22"},
    {"name": "read_humidity", "impl": read_humidity_impl, "hardware": "dht22"},
    {"name": "control_led", "impl": control_led_impl, "hardware": "led"},
    {"name": "control_relay", "impl": control_relay_impl, "hardware": "relay"},
    {"name": "read_button", "impl": read_button_impl, "hardware": "button"},
    {"name": "read_distance_ultrasonic", "impl": read_distance_ultrasonic_impl, "hardware": "hcsr04"},
    {"name": "read_distance_ir", "impl": read_distance_ir_impl, "hardware": "IR_GP2Y0A21YK0F"},
]


# --- Registration function ---

def register_tools(mcp: FastMCP, available_hardware: set[str]):
    """Enable/disable tools based on available_hardware."""
    for spec in TOOL_SPECS:
        enabled = spec["hardware"] in available_hardware
        if enabled:
            mcp.tool(enabled=enabled)(spec["impl"])
            print(f"Registered {spec['name']} enabled={enabled}")
