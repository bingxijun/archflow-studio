import importlib.util
import json
import os
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "plugins" / "archflow-studio" / "mcp" / "archflow_mcp_server.py"
SPEC = importlib.util.spec_from_file_location("archflow_mcp_server", SERVER_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class FakeClient:
    def call(self, action, params=None):
        return {"ok": True, "action": action, "params": params or {}}


class ArchFlowMcpServerTests(unittest.TestCase):
    def test_initialize_and_tool_list(self):
        initialized = MODULE.handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
        })
        self.assertEqual(initialized["result"]["protocolVersion"], "2025-11-25")
        listed = MODULE.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        names = {tool["name"] for tool in listed["result"]["tools"]}
        self.assertIn("sketchup_get_scene_info", names)
        self.assertIn("sketchup_run_archflow_script", names)
        self.assertNotIn("eval_ruby", names)

    def test_tool_call_maps_to_owned_bridge_protocol(self):
        called = MODULE.handle_request({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "sketchup_get_selection", "arguments": {}},
        }, FakeClient())
        self.assertFalse(called["result"]["isError"])
        self.assertEqual(called["result"]["structuredContent"]["action"], "get_selection")

    def test_tcp_client_uses_local_token_and_protocol(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = Path(directory) / "token"
            token_file.write_text("a" * 64, encoding="utf-8")
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            captured = {}

            def serve():
                connection, _ = listener.accept()
                with connection:
                    data = b""
                    while not data.endswith(b"\n"):
                        data += connection.recv(65536)
                    captured.update(json.loads(data.decode("utf-8")))
                    connection.sendall(b'{"ok":true,"result":{"bridge":"ArchFlow Bridge"}}\n')
                listener.close()

            thread = threading.Thread(target=serve)
            thread.start()
            environment = {
                "ARCHFLOW_BRIDGE_TOKEN_FILE": str(token_file),
                "ARCHFLOW_SKETCHUP_PORT": str(port),
            }
            with patch.dict(os.environ, environment, clear=False):
                result = MODULE.SketchUpBridgeClient().call("ping", {})
            thread.join(timeout=5)
            self.assertTrue(result["ok"])
            self.assertEqual(captured["protocol"], "archflow-sketchup/1")
            self.assertEqual(captured["token"], "a" * 64)
            self.assertEqual(captured["action"], "ping")


if __name__ == "__main__":
    unittest.main()
