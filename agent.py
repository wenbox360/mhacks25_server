# agent.py

import asyncio
import os
import json
from typing import Dict, Any, List
from fastmcp import Client
import anthropic
from dotenv import load_dotenv
import base64

load_dotenv(".env.local")
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY not found in .env.local")

USER_INPUT = "Get the robot to beep for 500ms and position the motor 90 degrees"
CLAUDE_MODEL = "claude-3-5-haiku-20241022" 

# --- Main Application ---
def format_tools_for_claude(mcp_tools: List[Any]) -> List[Dict[str, Any]]:
    """
    Convert FastMCP Tool objects (mcp.types.Tool) into a JSON-serializable
    schema suitable to pass to Claude/Anthropic.
    This is defensive: it accepts objects that expose .name/.description and
    several possible schema attribute names.
    """
    claude_tools = []

    for tool in mcp_tools:
        # read name & description as attributes
        name = getattr(tool, "name", None) or getattr(tool, "id", None)
        description = getattr(tool, "description", None) or getattr(tool, "title", None) or ""

        # The MCP Tool object may carry an input schema under several names.
        input_schema = (
            getattr(tool, "input_schema", None)
            or getattr(tool, "inputSchema", None)
            or getattr(tool, "schema", None)
            or getattr(tool, "inputSchemaJson", None)
            or {}
        )

        # If the input_schema uses 'properties' -> use them; otherwise try to
        # infer from a flattened parameters dict if present.
        properties = {}
        if isinstance(input_schema, dict) and "properties" in input_schema:
            properties = input_schema.get("properties", {})
        else:
            # some servers expose parameters as a dict-like attribute
            params = getattr(tool, "parameters", None) or getattr(tool, "params", None) or {}
            if isinstance(params, dict):
                for pname, pinfo in params.items():
                    ptype = pinfo.get("type", "string") if isinstance(pinfo, dict) else "string"
                    if ptype in ("int", "integer"):
                        properties[pname] = {"type": "integer", "description": f"Parameter: {pname}"}
                    elif ptype in ("float", "number"):
                        properties[pname] = {"type": "number", "description": f"Parameter: {pname}"}
                    else:
                        properties[pname] = {"type": "string", "description": f"Parameter: {pname}"}

        # If properties is still empty and the function signature is available,
        # you could optionally try to introspect it (not done here for simplicity).
        claude_tools.append({
            "name": name or "<unnamed_tool>",
            "description": description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": list(properties.keys())
            }
        })

    return claude_tools

def serialize_tool_result(result) -> dict:
    """
    Convert FastMCP CallToolResult to plain Python types.
    Returns a dict like {"ok": bool, "content": [...]}.
    """
    def ser_block(b):
        # Common MCP content shapes
        t = getattr(b, "type", None)
        if t == "text" and hasattr(b, "text"):
            return {"type": "text", "text": b.text}
        if t == "image" and hasattr(b, "data"):
            data = b.data
            if isinstance(data, (bytes, bytearray)):
                data = base64.b64encode(data).decode("utf-8")
            return {
                "type": "image",
                "mimeType": getattr(b, "mimeType", None) or getattr(b, "mime_type", None),
                "data": data,
            }
        # Fallback: try a generic mapping
        if hasattr(b, "__dict__"):
            # best-effort shallow dict
            d = {k: v for k, v in b.__dict__.items() if not k.startswith("_")}
            # stringify anything still non-serializable
            for k, v in list(d.items()):
                try:
                    json.dumps(v)
                except TypeError:
                    d[k] = str(v)
            return d
        return str(b)

    payload = {}
    payload["ok"] = not getattr(result, "is_error", False)
    if hasattr(result, "content"):
        blocks = result.content
        payload["content"] = [ser_block(b) for b in (blocks or [])]
    else:
        # last resort: stringify whole thing
        payload["content"] = [str(result)]
    return payload


async def main():
    """
    Main execution function to connect to the server, ask Claude for a tool call,
    and execute it.
    """
    # Initialize the FastMCP client to connect to your local server.py
    mcp_client = Client("server.py")
    
    # Initialize the Anthropic client. It will automatically use the
    # ANTHROPIC_API_KEY environment variable.
    try:
        claude_client = anthropic.Anthropic(api_key=api_key)
    except Exception as e:
        print(f"Error initializing Anthropic client: {e}")
        print("Please make sure your ANTHROPIC_API_KEY environment variable is set correctly.")
        return

    async with mcp_client:
        print("Pinging MCP server...")
        await mcp_client.ping()
        print("Ping successful.\n")
        print("Fetching available tools from MCP server...")
        available_mcp_tools = await mcp_client.list_tools()
        print(f"Found tools: {[tool.name for tool in available_mcp_tools]}\n")

        # 2. Format the tools for the Claude API
        claude_formatted_tools = format_tools_for_claude(available_mcp_tools)

        print(f"Sending user request to Claude: '{USER_INPUT}'")

        # 3. Send the user's request and the list of tools to Claude
        try:
            message = claude_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": USER_INPUT}],
                tools=claude_formatted_tools,
                tool_choice={"type": "auto"}
            )
        except Exception as e:
            print(f"An error occurred with the Claude API call: {e}")
            return
            
        print("Claude has responded. Analyzing for tool calls...")

        # 4. Check if Claude wants to call a tool
        if message.stop_reason == "tool_use":
            tool_calls = [content for content in message.content if content.type == "tool_use"]
            
            for tool_call in tool_calls:
                tool_name = tool_call.name
                tool_input = tool_call.input
                
                print(f"\nClaude decided to call the tool: '{tool_name}'")
                print(f"With arguments: {tool_input}")

                # 5. Execute the tool call using the MCP client
                try:
                    result = await mcp_client.call_tool(tool_name, tool_input)
                    print("\n--- Tool Execution Result ---")

                    print(json.dumps(serialize_tool_result(result), indent=2))
                    print("---------------------------\n")  

                    # (Optional) This is where you would send the result back to Claude
                    # to get a final natural language response. This is key for planning
                    # and multi-step tasks. We will just print the direct result for now.

                except Exception as e:
                    print(f"An error occurred while calling the tool '{tool_name}': {e}")

        else:
            # This happens if Claude responds without deciding to use a tool
            text_blocks = [b for b in message.content if getattr(b, "type", None) == "text"]
            final_response = text_blocks[0].text if text_blocks else ""
            print(f"\nClaude responded without a tool call: {final_response}")


if __name__ == "__main__":
    # Ensure the server is running before the agent tries to connect
    print("--- Make sure your server.py is running in a separate terminal ---")
    asyncio.run(main())