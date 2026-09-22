"""Regression coverage for non-face local acting layers."""
import tempfile
import unittest
from pathlib import Path

from make_extended_acting_fixture import build
from pipeline import read, validate


class ExtendedActingFixtureTests(unittest.TestCase):
    def test_head_hand_and_prop_layers_validate(self):
        with tempfile.TemporaryDirectory() as temp:
            project = build(Path(temp) / "project")
            errors = validate(project, assets=True)[1]
            self.assertEqual(errors, [])
            motion = read(project / "motion_plan.json")
            parts = {
                layer["acting"]["part"]
                for layer in motion["shots"][0]["layers"]
                if layer.get("acting") and layer["acting"].get("part") in {"head", "hand", "prop"}
            }
            self.assertEqual(parts, {"head", "hand", "prop"})


if __name__ == "__main__":
    unittest.main()
