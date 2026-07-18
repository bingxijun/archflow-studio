import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "plugins" / "archflow-studio" / "skills" / "archflow-studio"
SKILL = ROOT / "distributions" / "xiaohongshu" / "archflow"


@unittest.skipUnless(
    os.environ.get("ARCHFLOW_VALIDATE_XIAOHONGSHU") == "1",
    "Xiaohongshu distribution validation is intentionally separate from GitHub core CI",
)
class XiaohongshuSkillTests(unittest.TestCase):
    def test_original_skill_resources_are_present(self):
        source_files = {
            path.relative_to(SOURCE).as_posix()
            for path in SOURCE.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        packaged_files = {path.relative_to(SKILL).as_posix() for path in SKILL.rglob("*") if path.is_file()}
        transformed = {
            "scripts/CadBridge.psm1": "scripts/CadBridge.ps1",
            "assets/codex_cad_bridge.lsp": "assets/codex_cad_bridge.lsp.txt",
            "assets/templates/requirements_template.yaml": "assets/templates/requirements_template.yaml.txt",
            "assets/sketchup-extension/archflow_bridge.rb": "assets/sketchup-extension/archflow_bridge.rb.txt",
            "assets/sketchup-extension/archflow_bridge/main.rb": "assets/sketchup-extension/archflow_bridge/main.rb.txt",
        }
        intentionally_omitted = {"agents/openai.yaml", "assets/plugins/archflow_bridge.rbz"}
        expected = {transformed.get(path, path) for path in source_files if path not in intentionally_omitted}
        self.assertTrue(expected.issubset(packaged_files))

    def test_unmodified_core_files_match_original(self):
        adapted = {
            "SKILL.md",
            "agents/openai.yaml",
            "scripts/deploy_sketchup_mcp.ps1",
            "scripts/preflight_check.ps1",
            "scripts/setup_workstation.ps1",
            "scripts/build_sketchup_rbz.py",
            "scripts/cad-cli.ps1",
            "scripts/validate_skill_package.py",
            "references/autolisp-commands.md",
            "references/deployment.md",
            "references/permissions-and-security.md",
            "references/setup.md",
            "references/third-party-notices.md",
            "references/workstation-setup.md",
            "assets/integration-lock.json",
        }
        transformed = {
            "assets/codex_cad_bridge.lsp": "assets/codex_cad_bridge.lsp.txt",
            "assets/templates/requirements_template.yaml": "assets/templates/requirements_template.yaml.txt",
            "assets/sketchup-extension/archflow_bridge.rb": "assets/sketchup-extension/archflow_bridge.rb.txt",
            "assets/sketchup-extension/archflow_bridge/main.rb": "assets/sketchup-extension/archflow_bridge/main.rb.txt",
        }
        intentionally_omitted = {"agents/openai.yaml", "assets/plugins/archflow_bridge.rbz"}
        for source in SOURCE.rglob("*"):
            if not source.is_file() or "__pycache__" in source.parts or source.suffix == ".pyc":
                continue
            relative = source.relative_to(SOURCE).as_posix()
            if relative in adapted or relative in intentionally_omitted or relative == "scripts/CadBridge.psm1":
                continue
            packaged = SKILL / transformed.get(relative, relative)
            self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), hashlib.sha256(packaged.read_bytes()).digest(), relative)

    def test_package_validator(self):
        completed = subprocess.run(
            [sys.executable, str(SKILL / "scripts" / "validate_skill_package.py"), str(SKILL)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_upload_zip_has_skill_at_root(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "archflow.zip"
            completed = subprocess.run(
                [sys.executable, str(SKILL / "scripts" / "build_xhs_package.py"), "--output", str(output)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertLess(output.stat().st_size, 30 * 1024 * 1024)
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
                self.assertIn("SKILL.md", names)
                self.assertIn("scripts/archflow_mcp_server.py", names)
                self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))
                self.assertTrue(all(info.file_size <= 10 * 1024 * 1024 for info in archive.infolist()))
                allowed = {
                    ".md", ".txt", ".html", ".htm", ".css", ".js", ".py", ".java", ".cpp", ".c",
                    ".h", ".php", ".sh", ".bat", ".ps1", ".json", ".xml", ".sql", ".ini", ".cfg",
                    ".log", ".db", ".sqlite", ".sqlite3", ".mdb", ".accdb", ".sys",
                }
                self.assertTrue(all(Path(name).suffix.lower() in allowed for name in names))

    def test_standalone_mcp_server_lists_tools(self):
        path = SKILL / "scripts" / "archflow_mcp_server.py"
        spec = importlib.util.spec_from_file_location("xhs_archflow_mcp_server", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous
        response = module.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertIn("sketchup_bridge_status", names)
        self.assertIn("sketchup_capture_view", names)
        self.assertIn("sketchup_run_archflow_script", names)


if __name__ == "__main__":
    unittest.main()
