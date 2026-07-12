import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "archflow-studio"
SKILL = PLUGIN / "skills" / "archflow-studio"


class UnifiedSkillTests(unittest.TestCase):
    def test_plugin_manifest_matches_folder_and_semver(self):
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], PLUGIN.name)
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        self.assertEqual(manifest["license"], "Apache-2.0")
        self.assertEqual(manifest["author"]["name"], "OHDESIGN")
        self.assertEqual(manifest["interface"]["developerName"], "OHDESIGN")
        self.assertIn("https://archflow.best", manifest["description"])
        self.assertIn("https://archflow.best", manifest["interface"]["longDescription"])

        mcp = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))
        server = mcp["mcpServers"]["archflow-sketchup"]
        self.assertEqual(server["command"], "python")
        self.assertEqual(server["args"], ["./mcp/archflow_mcp_server.py"])
    def test_package_validator(self):
        completed = subprocess.run(
            [sys.executable, str(SKILL / "scripts" / "validate_skill_package.py"), str(SKILL)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_plugin_hashes_match_lock(self):
        lock = json.loads((SKILL / "assets" / "integration-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["sketchup_bridge"]["implementation"], "ArchFlow-owned")
        self.assertEqual(lock["sketchup_bridge"]["license"], "Apache-2.0")
        self.assertEqual([item["file"] for item in lock["bundled_plugins"]], ["plugins/archflow_bridge.rbz"])
        for item in lock["bundled_plugins"]:
            path = SKILL / "assets" / item["file"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(), item["sha256"])

    def test_only_archflow_sketchup_bridge_is_bundled(self):
        checked = [
            PLUGIN / "mcp" / "archflow_mcp_server.py",
            SKILL / "assets" / "sketchup-extension" / "archflow_bridge.rb",
            SKILL / "assets" / "sketchup-extension" / "archflow_bridge" / "main.rb",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in checked)
        self.assertIn("module ArchFlow", combined)
        self.assertIn("OHDESIGN", combined)
        self.assertIn("@heikikun", combined)
        self.assertIn("https://archflow.best", combined)
        self.assertNotIn("eval(", combined)

        self.assertEqual([path.name for path in (SKILL / "assets" / "plugins").glob("*.rbz")], ["archflow_bridge.rbz"])

    def test_developer_preview_notice_is_present_on_every_install_surface(self):
        required = [
            "ArchFlow Studio Developer Preview",
            "OHDESIGN",
            "@heikikun",
            "https://archflow.best",
            "当前为未签名开发者预览版。",
            "所有建筑、法规及施工输出必须由专业人员复核。",
        ]
        surfaces = [
            ROOT / "PREVIEW_NOTICE.txt",
            SKILL / "assets" / "sketchup-extension" / "archflow_bridge" / "main.rb",
        ]
        for surface in surfaces:
            content = surface.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{text!r} missing from {surface}")
        installer = (ROOT / "installer" / "windows" / "ArchFlow.Setup.ps1").read_text(encoding="utf-8")
        self.assertIn("Resolve-PreviewNoticePath", installer)
        self.assertIn("Write-PreviewNoticeForUser", installer)
        self.assertIn('Join-Path $InstallBase "PREVIEW_NOTICE.txt"', installer)

    def test_official_website_is_used_for_owned_schema_identifiers(self):
        project_schema = json.loads((ROOT / "schemas" / "archflow-project.schema.json").read_text(encoding="utf-8"))
        model_schema = json.loads((SKILL / "assets" / "templates" / "building_model_schema.json").read_text(encoding="utf-8"))
        self.assertTrue(project_schema["$id"].startswith("https://archflow.best/"))
        self.assertTrue(model_schema["$id"].startswith("https://archflow.best/"))
        source_files = [ROOT / "scripts" / "generate_sbom.py", ROOT / "README.md", ROOT / "NOTICE"]
        for path in source_files:
            content = path.read_text(encoding="utf-8")
            self.assertIn("https://archflow.best", content)
            self.assertNotIn("archflow.dev", content)

    def test_legal_archiver_rejects_non_official_sources(self):
        path = SKILL / "scripts" / "legal_evidence.py"
        spec = importlib.util.spec_from_file_location("legal_evidence", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        self.assertTrue(module.official_url("https://laws.e-gov.go.jp/law/325AC0000000201"))
        self.assertTrue(module.official_url("https://www.example-city.lg.jp/rules"))
        self.assertFalse(module.official_url("https://example.com/building-rules"))
        self.assertFalse(module.official_url("http://laws.e-gov.go.jp/law/325AC0000000201"))

    def test_optimizer_selects_feasible_improvement(self):
        path = SKILL / "scripts" / "design_optimizer.py"
        spec = importlib.util.spec_from_file_location("design_optimizer", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline"
            candidate = root / "candidate"
            baseline.mkdir()
            candidate.mkdir()
            (baseline / "metrics.json").write_text(json.dumps({"gross_floor_area_m2": 80.0}), encoding="utf-8")
            (candidate / "metrics.json").write_text(json.dumps({"gross_floor_area_m2": 95.0}), encoding="utf-8")
            validation = {"status": "WARNING", "checks": []}
            (baseline / "validation_report.json").write_text(json.dumps(validation), encoding="utf-8")
            (candidate / "validation_report.json").write_text(json.dumps(validation), encoding="utf-8")
            objectives = root / "objectives.json"
            objectives.write_text(
                json.dumps({"objectives": [{"id": "area", "metric": "gross_floor_area_m2", "direction": "target", "target": 100.0, "weight": 1.0}]}),
                encoding="utf-8",
            )
            report = module.compare(baseline, candidate, objectives)
            self.assertEqual(report["selected_quantitative_candidate"], "candidate")
            self.assertGreater(report["candidate_score"], 0)


if __name__ == "__main__":
    unittest.main()
