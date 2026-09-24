"""Behavior tests for the V1.0 project state helper."""
import json
import tempfile
import unittest
from pathlib import Path

from project_state import init, open_revision_entries, record_revision, route_feedback, transition, update_revision


class ProjectStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        self.project.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_init_and_transition_record_history(self):
        self.assertEqual(init(self.project)["state"], "INIT")
        value = transition(self.project, "STORY", "brief received", ["confirm dialogue"])
        self.assertEqual(value["state"], "STORY")
        self.assertEqual(value["history"][0]["from"], "INIT")
        saved = json.loads((self.project / "project_state.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["pending"], ["confirm dialogue"])

    def test_invalid_transition_is_rejected(self):
        init(self.project)
        with self.assertRaises(ValueError):
            transition(self.project, "FINAL", "skip")

    def test_revision_can_route_back_to_storyboard(self):
        init(self.project)
        transition(self.project, "STORY", "brief")
        transition(self.project, "STORYBOARD", "beats ready")
        transition(self.project, "REVISION", "user feedback")
        value = transition(self.project, "STORYBOARD", "repair shot continuity")
        self.assertEqual(value["state"], "STORYBOARD")

    def test_feedback_routes_to_smallest_module(self):
        self.assertEqual(route_feedback("人物一直晃" )["module"], "motion_naturalness")
        self.assertEqual(route_feedback("字幕太快" )["state"], "AUDIO")
        self.assertEqual(route_feedback("背景像换了地方" )["state"], "STORYBOARD")

    def test_unknown_feedback_requires_manual_revision(self):
        self.assertEqual(route_feedback("我觉得有点怪" )["state"], "REVISION")

    def test_revision_log_routes_and_updates_feedback(self):
        entry = record_revision(self.project, "字幕太快", shot="shot_002")
        self.assertEqual(entry["module"], "subtitle_sync")
        self.assertEqual(entry["shot"], "shot_002")
        open_items, error = open_revision_entries(self.project)
        self.assertIsNone(error)
        self.assertEqual([item["id"] for item in open_items], [entry["id"]])
        updated = update_revision(self.project, entry["id"], "resolved", "已重新预览")
        self.assertEqual(updated["status"], "resolved")
        self.assertEqual(open_revision_entries(self.project)[0], [])


if __name__ == "__main__":
    unittest.main()
