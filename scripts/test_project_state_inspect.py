"""Tests for read-only workflow state inspection."""
import json
import tempfile
import unittest
from pathlib import Path

from project_state import inspect


class ProjectStateInspectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        self.project.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, value):
        (self.project / name).write_text(json.dumps(value), encoding="utf-8")

    def seed_ready_project(self):
        self.write("production_brief.json", {"project_id": "demo"})
        self.write("characters.json", {"characters": [{"id": "lin", "reference": {"status": "ready"}}]})
        self.write("storyboard.json", {"shots": [{"id": "s1", "direction": {"scene_id": "scene"}}]})
        self.write("motion_plan.json", {"asset_mode": "fixture", "shots": [{"shot_id": "s1"}]})

    def test_empty_project_is_init(self):
        result = inspect(self.project)
        self.assertEqual(result["suggested_state"], "INIT")

    def test_brief_without_characters_needs_character_stage(self):
        self.write("production_brief.json", {"project_id": "demo"})
        self.assertEqual(inspect(self.project)["suggested_state"], "CHARACTER")

    def test_invalid_quality_report_routes_to_quality_check(self):
        self.write("production_brief.json", {"project_id": "demo"})
        self.write("characters.json", {"characters": []})
        self.write("storyboard.json", {"shots": [{"id": "s1", "direction": {}}]})
        self.assertEqual(inspect(self.project)["suggested_state"], "STORYBOARD")

    def test_changed_asset_report_routes_back_to_animation(self):
        self.seed_ready_project()
        self.write("asset_report.json", {"shots": [{"shot_id": "s1", "changed": True, "missing": []}]})
        result = inspect(self.project)
        self.assertEqual(result["suggested_state"], "ANIMATION")
        self.assertIn("asset fingerprint review: s1", result["missing"])

    def test_missing_asset_report_files_routes_back_to_animation(self):
        self.seed_ready_project()
        self.write("asset_report.json", {"shots": [{"shot_id": "s1", "changed": False, "missing": ["shots/s1/master.png"]}]})
        result = inspect(self.project)
        self.assertEqual(result["suggested_state"], "ANIMATION")
        self.assertIn("missing assets: s1: shots/s1/master.png", result["missing"])

    def test_pending_visual_review_keeps_project_in_preview(self):
        self.seed_ready_project()
        self.write("quality_report.json", {"status": "PASS"})
        (self.project / "preview.mp4").write_bytes(b"preview")
        (self.project / "visual-review").mkdir()
        (self.project / "visual-review" / "s1_first.png").write_bytes(b"frame")
        self.write("visual_review.json", {
            "preview": "preview.mp4",
            "review_status": "pending",
            "frames": [{"shot_id": "s1", "position": "first", "image": "visual-review/s1_first.png", "reviewed": False}],
        })
        result = inspect(self.project)
        self.assertEqual(result["suggested_state"], "PREVIEW")
        self.assertIn("review frame not checked: s1 first", result["missing"])
        self.assertIn("visual_review.json review_status=approved", result["missing"])

    def test_malformed_evidence_is_reported_instead_of_crashing(self):
        self.seed_ready_project()
        (self.project / "asset_report.json").write_text("[]", encoding="utf-8")
        result = inspect(self.project)
        self.assertEqual(result["suggested_state"], "ANIMATION")
        self.assertIn("valid asset_report.json", result["missing"])


if __name__ == "__main__":
    unittest.main()
