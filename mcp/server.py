"""Sprecher MCP Server - Tools for AI agents via Claude Code MCP."""

import json
import sys
from typing import Any

# MCP protocol types
PROTOCOL_VERSION = "2024-11-05"


class MCPError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def send_response(req_id: Any, result: Any):
    """Send a JSON-RPC response to stdout."""
    response = {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result,
    }
    print(json.dumps(response), flush=True)


def send_error(req_id: Any, code: int, message: str):
    """Send a JSON-RPC error to stdout."""
    response = {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }
    print(json.dumps(response), flush=True)


def send_notification(method: str, params: dict):
    """Send a JSON-RPC notification (no id)."""
    response = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    }
    print(json.dumps(response), flush=True)


# Tool definitions
TOOLS = [
    {
        "name": "sprecher_speak",
        "description": "Generate speech from text using Kokoro ONNX TTS. Fast, high-quality voice synthesis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to speak"},
                "voice": {"type": "string", "description": "Voice key (e.g., 'bf_isabella', 'am_adam'). Use sprecher_list_voices to see available options.", "default": "bf_isabella"},
                "speed": {"type": "number", "description": "Speech speed (0.5-2.0, default 1.0)", "default": 1.0},
                "audio_format": {"type": "string", "description": "Output format: 'wav' or 'mp3'", "default": "wav"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "sprecher_list_voices",
        "description": "List all available Kokoro TTS voices with metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "gender": {"type": "string", "description": "Filter by gender: 'female' or 'male'", "default": None},
                "language": {"type": "string", "description": "Filter by language code (e.g., 'en-us')", "default": None},
            },
        },
    },
    {
        "name": "sprecher_transcribe",
        "description": "Transcribe audio to text using Whisper STT.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "audio_path": {"type": "string", "description": "Path to audio file to transcribe"},
                "language": {"type": "string", "description": "Language code (e.g., 'en'). Auto-detected if not specified.", "default": None},
            },
            "required": ["audio_path"],
        },
    },
    {
        "name": "sprecher_health",
        "description": "Check if Sprecher service is running and healthy.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "sprecher_get_job",
        "description": "Get job status and details.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "integer", "description": "Job ID to query"},
            },
            "required": ["job_id"],
        },
    },
]


async def call_sprecher_api(endpoint: str, method: str = "GET", data: dict | None = None):
    """Call the Sprecher API."""
    import urllib.request
    import urllib.error

    base_url = "http://127.0.0.1:8400"
    url = f"{base_url}{endpoint}"

    # Get API key from environment
    api_key = ""
    try:
        from config import API_KEY
        api_key = API_KEY
    except ImportError:
        pass

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req_data = json.dumps(data).encode() if data else None

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "message": e.read().decode()}
    except Exception as e:
        return {"error": -1, "message": str(e)}


async def tool_sprecher_speak(text: str, voice: str = "bf_isabella", speed: float = 1.0, audio_format: str = "wav") -> dict:
    """Handle sprecher_speak tool call."""
    result = await call_sprecher_api(
        "/api/tts/sync",
        method="POST",
        data={"text": text, "voice": voice, "speed": speed, "audio_format": audio_format},
    )
    if "error" in result:
        raise MCPError(result["error"], result.get("message", "TTS generation failed"))
    return result


async def tool_sprecher_list_voices(gender: str = None, language: str = None) -> dict:
    """Handle sprecher_list_voices tool call."""
    params = []
    if gender:
        params.append(f"gender={gender}")
    if language:
        params.append(f"language={language}")
    query = "?" + "&".join(params) if params else ""
    result = await call_sprecher_api(f"/api/tts/voices{query}")
    if "error" in result:
        raise MCPError(result["error"], result.get("message", "Failed to list voices"))
    return result


async def tool_sprecher_transcribe(audio_path: str, language: str = None) -> dict:
    """Handle sprecher_transcribe tool call."""
    import urllib.request
    import urllib.error

    base_url = "http://127.0.0.1:8400"

    # Get API key from environment
    api_key = ""
    try:
        from config import API_KEY
        api_key = API_KEY
    except ImportError:
        pass

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Multipart form upload
    boundary = b"----SprecherBoundary"
    with open(audio_path, "rb") as f:
        audio_data = f.read()

    body = b""
    body += b"--" + boundary + b"\r\n"
    body += b'Content-Disposition: form-data; name="audio_file"; filename="audio.wav"\r\n'
    body += b"Content-Type: audio/wav\r\n\r\n"
    body += audio_data
    body += b"\r\n--" + boundary + b"--\r\n"

    headers["Content-Type"] = f"multipart/form-data; boundary=----SprecherBoundary"
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        f"{base_url}/api/stt/sync",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "message": e.read().decode()}
    except Exception as e:
        return {"error": -1, "message": str(e)}


async def tool_sprecher_health() -> dict:
    """Handle sprecher_health tool call."""
    result = await call_sprecher_api("/api/health")
    return result


async def tool_sprecher_get_job(job_id: int) -> dict:
    """Handle sprecher_get_job tool call."""
    result = await call_sprecher_api(f"/api/jobs/{job_id}")
    return result


TOOL_HANDLERS = {
    "sprecher_speak": tool_sprecher_speak,
    "sprecher_list_voices": tool_sprecher_list_voices,
    "sprecher_transcribe": tool_sprecher_transcribe,
    "sprecher_health": tool_sprecher_health,
    "sprecher_get_job": tool_sprecher_get_job,
}


def handle_request(req: dict):
    """Handle incoming JSON-RPC request."""
    method = req.get("method", "")
    req_id = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        send_response(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": {"name": "sprecher", "version": "0.1.0"},
            "capabilities": {"tools": {}},
        })
        return

    if method == "notifications/initialized":
        # Client initialized, nothing to do
        return

    if method == "tools/list":
        send_response(req_id, {"tools": TOOLS})
        return

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in TOOL_HANDLERS:
            send_error(req_id, -32601, f"Unknown tool: {tool_name}")
            return

        import asyncio

        async def run_tool():
            handler = TOOL_HANDLERS[tool_name]
            try:
                result = await handler(**arguments)
                send_response(req_id, {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2),
                        }
                    ]
                })
            except MCPError as e:
                send_error(req_id, e.code, e.message)
            except Exception as e:
                send_error(req_id, -32603, str(e))

        asyncio.run(run_tool())
        return

    send_error(req_id, -32601, f"Unknown method: {method}")


def main():
    """Main MCP server loop."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            handle_request(req)
        except json.JSONDecodeError:
            continue
        except Exception as e:
            send_error(None, -32603, str(e))


if __name__ == "__main__":
    main()
