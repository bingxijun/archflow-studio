import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from archflow.pipeline import discover_core_skill, doctor, run_project


class PipelineTests(unittest.TestCase):
    def test_explicit_core_skill_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "scripts" / "architectural_pipeline.py"
            script.parent.mkdir(parents=True)
            script.write_text("print('ok')\n", encoding="utf-8")
            self.assertEqual(discover_core_skill(str(root)), root.resolve())

    def test_doctor_reports_missing_explicit_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"ARCHFLOW_CORE_SKILL": ""}, clear=False):
                report = doctor(str(Path(directory) / "missing"))
            self.assertIn(report["status"], {"ready", "degraded"})
            self.assertIn("archflow-studio", report["capabilities"])

    def test_plan_has_millisecond_run_id_and_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "skill"
            script = skill / "scripts" / "architectural_pipeline.py"
            script.parent.mkdir(parents=True)
            script.write_text("print('ok')\n", encoding="utf-8")
            (root / "model.json").write_text("{}", encoding="utf-8")
            manifest = {
                "schema_version": "0.1",
                "project": {"id": "p", "title": "P", "mode": "concept"},
                "inputs": {"site_cad": None, "requirements": None, "legal_sources": []},
                "model": {"building_model": "model.json"},
                "pipeline": {"output_root": "outputs", "execute_sketchup": False},
            }
            manifest_path = root / "archflow.project.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            plan = run_project(manifest_path, "build", str(skill), plan_only=True)
            self.assertRegex(plan["run_id"], r"^\d{8}T\d{9}Z-[0-9a-f]{8}$")
            self.assertFalse(plan["mutates_source_cad"])
            self.assertFalse(plan["executes_sketchup"])


if __name__ == "__main__":
    unittest.main()
