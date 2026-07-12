import json
import tempfile
import unittest
from pathlib import Path

from archflow.project import ProjectError, fingerprint, resolve_portable_path, validate_manifest


class ProjectTests(unittest.TestCase):
    def test_path_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ProjectError):
                resolve_portable_path(Path(directory), "../secret.dwg", "inputs.site_cad")

    def test_manifest_rejects_sketchup_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "model.json").write_text("{}", encoding="utf-8")
            manifest = {
                "schema_version": "0.1",
                "project": {"id": "p", "title": "P", "mode": "concept"},
                "inputs": {"site_cad": None, "requirements": None, "legal_sources": []},
                "model": {"building_model": "model.json"},
                "pipeline": {"output_root": "outputs", "execute_sketchup": True},
            }
            issues = validate_manifest(manifest, root)
            self.assertIn("pipeline.execute_sketchup must remain false in manifest schema 0.1", issues)

    def test_fingerprint_is_stable(self):
        inventory = [{"role": "model", "path": "model.json", "sha256": "abc"}]
        self.assertEqual(fingerprint(inventory), fingerprint(json.loads(json.dumps(inventory))))


if __name__ == "__main__":
    unittest.main()
