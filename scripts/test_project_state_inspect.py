"""Tests for read-only workflow state inspection."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from project_state import file_sha256, inspect, record_revision, review, source_fingerprint


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
        source = Path(__file__).resolve().parents[1] / "examples" / "library"
        shutil.copytree(source, self.project, dirs_exist_ok=True)
        characters = json.loads((self.project / "characters.json").read_text(encoding="utf-8"))
        characters["characters"][0]["reference"]["status"] = "ready"
        self.write("characters.json", characters)
        storyboard = json.loads((self.project / "storyboard.json").read_text(encoding="utf-8"))
        shot_ids = [shot["id"] for shot in storyboard["shots"]]
        for index, shot in enumerate(storyboard["shots"]):
            shot["direction"] = {
                "scene_id": "scene",
                "camera_position": "eye_level",
                "background_view": "library",
                "view_id": f"view_{index + 1}",
                "incoming_state": "stable",
                "outgoing_state": "stable",
                "micro_actions": "none",
                "cut_reason": "continue",
                "next_shot_id": shot_ids[index + 1] if index + 1 < len(shot_ids) else None,
                "handoff": "continue",
                "reaction_hold_frames": 0,
                "listening_reactions": [],
            }
        self.write("storyboard.json", storyboard)

    def test_empty_project_is_init(self):
        result = inspect(self.project)
        self.assertEqual(result["suggested_state"], "INIT")

    def test_brief_without_characters_needs_character_stage(self):
        self.write("production_brief.json", {"project_id": "demo"})
        result = inspect(self.project)
        self.assertEqual(result["suggested_state"], "INIT")
        self.assertTrue(result["schema_errors"])

    def test_invalid_quality_report_routes_to_quality_check(self):
        self.write("production_brief.json", {"project_id": "demo"})
        self.write("characters.json", {"characters": []})
        self.write("storyboard.json", {"shots": [{"id": "s1", "direction": {}}]})
        self.assertEqual(inspect(self.project)["suggested_state"], "INIT")

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

    def seed_review_project(self):
        self.seed_ready_project()
        self.write("quality_report.json", {"status": "PASS"})
        (self.project / "preview.mp4").write_bytes(b"preview")
        (self.project / "visual-review").mkdir()
        image = self.project / "visual-review" / "s1_first.png"
        image.write_bytes(b"frame")
        self.write("visual_review.json", {
            "version": "0.1",
            "preview": "preview.mp4",
            "preview_sha256": file_sha256(self.project / "preview.mp4"),
            "source_fingerprint": source_fingerprint(self.project),
            "frames": [{
                "shot_id": "s1", "position": "first", "image": "visual-review/s1_first.png",
                "sha256": file_sha256(image), "reviewed": False,
            }],
            "review_status": "pending",
        })

    def test_approve_review_updates_all_frames(self):
        self.seed_review_project()
        result = review(self.project, approved=True, note="已查看", reviewer="tester")
        self.assertEqual(result["review_status"], "approved")
        self.assertTrue(result["frames"][0]["reviewed"])
        self.assertEqual(result["reviewer"], "tester")
        self.assertEqual(inspect(self.project)["suggested_state"], "PREVIEW")

    def test_rejected_review_routes_to_revision(self):
        self.seed_review_project()
        review(self.project, note="shot_001 接缝明显")
        result = inspect(self.project)
        self.assertEqual(result["suggested_state"], "REVISION")
        self.assertIn("rev_001: shot_001 接缝明显", result["missing"])

    def test_approval_refuses_stale_source(self):
        self.seed_review_project()
        self.write("storyboard.json", {"shots": [{"id": "s1", "direction": {"scene_id": "changed"}}]})
        with self.assertRaisesRegex(ValueError, "stale"):
            review(self.project, approved=True)

    def test_approved_review_becomes_stale_after_source_edit(self):
        self.seed_review_project()
        review(self.project, approved=True)
        motion = json.loads((self.project / "motion_plan.json").read_text(encoding="utf-8"))
        motion["asset_mode"] = "preview"
        self.write("motion_plan.json", motion)
        result = inspect(self.project)
        self.assertEqual(result["suggested_state"], "PREVIEW")
        self.assertIn("visual review source fingerprint is stale", result["missing"])

    def test_open_revision_log_takes_priority(self):
        self.seed_review_project()
        entry = record_revision(self.project, "shot_001 动作太僵", shot="shot_001")
        result = inspect(self.project)
        self.assertEqual(result["suggested_state"], "REVISION")
        self.assertIn(entry["id"] + ": shot_001 动作太僵", result["missing"])

    def test_malformed_evidence_is_reported_instead_of_crashing(self):
        self.seed_ready_project()
        (self.project / "asset_report.json").write_text("[]", encoding="utf-8")
        result = inspect(self.project)
        self.assertEqual(result["suggested_state"], "ANIMATION")
        self.assertIn("valid asset_report.json", result["missing"])

    def test_malformed_quality_report_is_reported_instead_of_crashing(self):
        self.seed_ready_project()
        (self.project / "quality_report.json").write_text("[]", encoding="utf-8")
        result = inspect(self.project)
        self.assertEqual(result["suggested_state"], "QUALITY_CHECK")
        self.assertIn("valid quality_report.json", result["missing"])


if __name__ == "__main__":
    unittest.main()
