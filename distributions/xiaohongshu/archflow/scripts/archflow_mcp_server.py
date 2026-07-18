#!/usr/bin/env python3
"""ArchFlow-owned MCP stdio server for the local SketchUp bridge.

SPDX-FileCopyrightText: 2026 OHDESIGN
SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import os
import secrets
import socket
import sys
from pathlib import Path
from typing import Any


SERVER_VERSION = "0.2.0"
PROTOCOL_VERSION = "2025-11-25"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9877
OFFICIAL_WEBSITE = "https://archflow.best"


def token_path() -> Path:
    override = os.environ.get("ARCHFLOW_BRIDGE_TOKEN_FILE")
    if override:
        return Path(override).expanduser()
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return base / "ArchFlow" / "bridge-token"


def ensure_token(path: Path | None = None) -> str:
    path = path or token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if len(value) >= 32:
            return value
    value = secrets.token_hex(32)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        existing = path.read_text(encoding="utf-8").strip()
        if len(existing) >= 32:
            return existing
        path.write_text(value, encoding="utf-8")
    else:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
    return value


class BridgeError(RuntimeError):
    pass


class SketchUpBridgeClient:
    def __init__(self) -> None:
        self.host = os.environ.get("ARCHFLOW_SKETCHUP_HOST", DEFAULT_HOST)
        self.port = int(os.environ.get("ARCHFLOW_SKETCHUP_PORT", str(DEFAULT_PORT)))
        self.timeout = float(os.environ.get("ARCHFLOW_SKETCHUP_TIMEOUT", "30"))

    def call(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request = {
            "protocol": "archflow-sketchup/1",
            "token": ensure_token(),
            "action": action,
            "params": params or {},
        }
        payload = (json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as stream:
                stream.settimeout(self.timeout)
                stream.sendall(payload)
                response = bytearray()
                while not response.endswith(b"\n"):
                    block = stream.recv(65536)
                    if not block:
                        break
                    response.extend(block)
                    if len(response) > 8 * 1024 * 1024:
                        raise BridgeError("SketchUp response exceeded 8 MiB")
        except OSError as exc:
            raise BridgeError(
                f"ArchFlow SketchUp Bridge is unavailable at {self.host}:{self.port}. "
                "Open SketchUp and enable the ArchFlow Bridge extension."
            ) from exc
        if not response:
            raise BridgeError("SketchUp closed the connection without a response")
        try:
            result = json.loads(response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BridgeError("SketchUp returned an invalid bridge response") from exc
        if not isinstance(result, dict):
            raise BridgeError("SketchUp returned a non-object bridge response")
        if not result.get("ok"):
            raise BridgeError(str(result.get("error") or "SketchUp operation failed"))
        return result


EMPTY_SCHEMA = {"type": "object", "additionalProperties": False}
ENTITY_ID = {"type": "integer", "minimum": 1, "description": "SketchUp persistent entity ID."}


TOOLS: list[dict[str, Any]] = [
    {
        "name": "sketchup_bridge_status",
        "title": "SketchUp bridge status",
        "description": "Check the local ArchFlow-owned SketchUp bridge without changing the model.",
        "inputSchema": EMPTY_SCHEMA,
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "sketchup_get_scene_info",
        "title": "Read SketchUp scene",
        "description": "Read model, units, top-level entity, tag, material, and selection information.",
        "inputSchema": EMPTY_SCHEMA,
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "sketchup_get_selection",
        "title": "Read SketchUp selection",
        "description": "Read persistent IDs, types, names, tags, and bounds for selected entities.",
        "inputSchema": EMPTY_SCHEMA,
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "sketchup_create_box",
        "title": "Create SketchUp box",
        "description": "Create a named grouped rectangular prism. All coordinates and dimensions are millimetres.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1, "maxLength": 200},
                "position_mm": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                "dimensions_mm": {"type": "array", "items": {"type": "number", "exclusiveMinimum": 0}, "minItems": 3, "maxItems": 3},
                "tag": {"type": "string", "maxLength": 200},
            },
            "required": ["name", "position_mm", "dimensions_mm"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
    },
    {
        "name": "sketchup_transform_entity",
        "title": "Transform SketchUp entity",
        "description": "Translate, rotate about the entity centre, or scale an entity. Translation uses millimetres and rotation uses degrees.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": ENTITY_ID,
                "translation_mm": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                "rotation_deg": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                "scale": {"type": "array", "items": {"type": "number", "exclusiveMinimum": 0}, "minItems": 3, "maxItems": 3},
            },
            "required": ["entity_id"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
    },
    {
        "name": "sketchup_set_material",
        "title": "Set SketchUp material",
        "description": "Assign or create a material on an entity using a #RRGGBB colour and optional opacity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": ENTITY_ID,
                "material_name": {"type": "string", "minLength": 1, "maxLength": 200},
                "color": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
                "opacity": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["entity_id", "material_name", "color"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "sketchup_delete_entity",
        "title": "Delete SketchUp entity",
        "description": "Delete one entity by persistent ID. Use only after the user explicitly approves deletion.",
        "inputSchema": {"type": "object", "properties": {"entity_id": ENTITY_ID}, "required": ["entity_id"], "additionalProperties": False},
        "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
    },
    {
        "name": "sketchup_export_scene",
        "title": "Export SketchUp scene",
        "description": "Export the active model to an explicit local path supported by the installed SketchUp edition.",
        "inputSchema": {
            "type": "object",
            "properties": {"output_path": {"type": "string", "minLength": 1}},
            "required": ["output_path"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "sketchup_capture_view",
        "title": "Capture SketchUp render view",
        "description": "Capture the current camera or a named ArchFlow scene to a PNG for geometry-preserving image rendering. This writes an image file but does not change model geometry.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "output_path": {"type": "string", "minLength": 1},
                "view": {"enum": ["current", "front", "right", "top", "axon"]},
                "width": {"type": "integer", "minimum": 320, "maximum": 4096, "default": 2000},
                "height": {"type": "integer", "minimum": 320, "maximum": 4096, "default": 1600},
            },
            "required": ["output_path", "view"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "sketchup_run_archflow_script",
        "title": "Run verified ArchFlow script",
        "description": "Run a local Ruby file generated by ArchFlow after verifying its SHA-256 and required header. Call only after the user explicitly approves model mutation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "script_path": {"type": "string", "minLength": 1},
                "sha256": {"type": "string", "pattern": "^[0-9A-Fa-f]{64}$"},
                "confirmed": {"const": True},
            },
            "required": ["script_path", "sha256", "confirmed"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
    },
]


TOOL_ACTIONS = {
    "sketchup_bridge_status": "ping",
    "sketchup_get_scene_info": "get_scene_info",
    "sketchup_get_selection": "get_selection",
    "sketchup_create_box": "create_box",
    "sketchup_transform_entity": "transform_entity",
    "sketchup_set_material": "set_material",
    "sketchup_delete_entity": "delete_entity",
    "sketchup_export_scene": "export_scene",
    "sketchup_capture_view": "capture_view",
    "sketchup_run_archflow_script": "run_archflow_script",
}


def result_payload(data: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
        "structuredContent": data,
        "isError": is_error,
    }


def response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def protocol_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_request(message: dict[str, Any], client: SketchUpBridgeClient | None = None) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None
    if method == "initialize":
        requested = message.get("params", {}).get("protocolVersion")
        selected = requested if requested in {"2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"} else PROTOCOL_VERSION
        return response(request_id, {
            "protocolVersion": selected,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "archflow-sketchup", "title": "ArchFlow SketchUp Bridge", "version": SERVER_VERSION},
            "instructions": f"Use read-only tools first. Mutating tools require an explicit user request and SketchUp Undo remains available. Official website: {OFFICIAL_WEBSITE}",
        })
    if method == "ping":
        return response(request_id, {})
    if method == "tools/list":
        return response(request_id, {"tools": TOOLS})
    if method != "tools/call":
        return protocol_error(request_id, -32601, f"Method not found: {method}")
    params = message.get("params") or {}
    name = params.get("name")
    action = TOOL_ACTIONS.get(name)
    if not action:
        return protocol_error(request_id, -32602, f"Unknown tool: {name}")
    arguments = params.get("arguments") or {}
    if not isinstance(arguments, dict):
        return protocol_error(request_id, -32602, "Tool arguments must be an object")
    try:
        data = (client or SketchUpBridgeClient()).call(action, arguments)
        return response(request_id, result_payload(data))
    except (BridgeError, ValueError, OSError) as exc:
        return response(request_id, result_payload({"ok": False, "error": str(exc)}, is_error=True))


def main() -> int:
    for raw_line in sys.stdin.buffer:
        try:
            message = json.loads(raw_line.decode("utf-8-sig"))
            if not isinstance(message, dict):
                raise ValueError("MCP message must be a JSON object")
            outgoing = handle_request(message)
        except Exception as exc:  # Keep the stdio process alive for the next valid request.
            outgoing = protocol_error(None, -32700, f"Invalid request: {exc}")
        if outgoing is not None:
            sys.stdout.write(json.dumps(outgoing, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
