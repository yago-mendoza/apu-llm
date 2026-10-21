"""A minimal MCP server over stdio, so Claude Code (or any MCP client) can hand tasks to the local model.

Register it once:   claude mcp add --scope user apu -- apu mcp

The protocol is JSON-RPC 2.0, one message per line on stdin/stdout. Only the parts a tool
server needs are implemented: initialize, tools/list, tools/call, ping. Nothing but protocol
messages may go to stdout; diagnostics go to stderr.
"""

import json
import sys
from pathlib import Path

from . import __version__
from .cli import build_messages, run_chat, _placement
from .ollama import EngineDown, Ollama

PROTOCOL = "2025-06-18"

TOOLS = [
    {
        "name": "local_llm_ask",
        "description": (
            "Ask the local model running on this laptop (offline, free, private; slower and weaker than you). "
            "Good for: summarising or classifying long text, extracting fields, first drafts, bulk mechanical "
            "work, anything that must not leave the machine. Not for: hard reasoning, multi-file code changes, "
            "or facts that need to be current. Pass file paths in `files` instead of pasting their content. "
            "Check its answer before relying on it."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The task, written for a capable but literal assistant."},
                "files": {"type": "array", "items": {"type": "string"},
                          "description": "Absolute paths of text files to include as context."},
                "system": {"type": "string", "description": "Optional system prompt."},
                "think": {"type": "boolean", "description": "Let the model reason first: slower, better on hard tasks."},
                "max_tokens": {"type": "integer", "description": "Cap on the reply length."},
                "model": {"type": "string", "description": "Override the default local model."},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "local_llm_status",
        "description": "Whether the local model is up, which models exist, what is loaded and how fast it ran last.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _text(s: str, is_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": s}], "isError": is_error}


def _ask(cfg, a: dict) -> dict:
    missing = [f for f in a.get("files", []) if not Path(f).is_file()]
    if missing:
        return _text(f"These files do not exist: {', '.join(missing)}", True)
    messages = build_messages(a["prompt"], a.get("files", []), None, a.get("system"))
    text, stats = run_chat(cfg, messages, model=a.get("model"), think=a.get("think"),
                           max_tokens=a.get("max_tokens"), source="mcp")
    footer = f"\n\n[local model {a.get('model') or cfg['model']} · {stats.line()}]" if stats else ""
    return _text(text + footer)


def _status(cfg) -> dict:
    eng = Ollama(cfg["host"])
    lines = [f"Ollama {eng.version()} at {cfg['host']}", f"default model: {cfg['model']} (ctx {cfg['ctx']})"]
    lines.append("downloaded: " + ", ".join(sorted(m["name"] for m in eng.models())))
    loaded = eng.loaded()
    lines += [f"loaded: {m['name']} · {_placement(m)}" for m in loaded] or ["loaded: nothing (first call will load, ~10-30 s)"]
    return _text("\n".join(lines))


def handle(cfg, msg: dict):
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:  # notifications (e.g. notifications/initialized) get no reply
        return None
    if method == "initialize":
        result = {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                  "serverInfo": {"name": "apu", "version": __version__}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        name, args = msg["params"]["name"], msg["params"].get("arguments", {})
        try:
            if name == "local_llm_ask":
                result = _ask(cfg, args)
            elif name == "local_llm_status":
                result = _status(cfg)
            else:
                return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"Unknown tool {name}"}}
        except EngineDown as e:
            result = _text(f"{e}. The local model is not running; tell the user to start the Ollama app.", True)
        except Exception as e:  # a tool failure is reported to the model, not raised as a protocol error
            result = _text(f"{type(e).__name__}: {e}", True)
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def serve(cfg) -> int:
    stdin = open(sys.stdin.fileno(), "r", encoding="utf-8", closefd=False)
    for line in stdin:
        if not line.strip():
            continue
        try:
            reply = handle(cfg, json.loads(line))
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0
