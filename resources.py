# resources.py

import uuid
import time
from fastmcp import FastMCP, Context
from readQueue import get_recent_values

def register_resources(mcp: FastMCP):
    """Register all resources with the MCP server."""
    
    @mcp.resource("sensor://ir/GP2Y0A21YK0F", enabled=False)
    async def get_ir_sensor_reading(context: Context) -> str:
        """Get reading from IR sensor model."""
       
        values = get_recent_values(40)
        if values:
            # Take last 10 values, convert to float, and average
            last_10 = values[-10:] if len(values) >= 10 else values
            try:
                avg = sum(float(v) for v in last_10) / len(last_10)
                return f"{avg:.2f} cm"
            except Exception:
                return "Invalid value(s)"
        return "No value"