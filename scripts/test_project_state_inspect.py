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


if __name__ == "__main__":
    unittest.main()
