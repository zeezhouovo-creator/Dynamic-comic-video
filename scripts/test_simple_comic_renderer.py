"""Regression checks for simple-comic face acting and exact timing."""
import json
import tempfile
import unittest
from pathlib import Path

from generate_simple_comic_motion_assets import _box
from render_simple_comic_preview import _ass_time, _load_motion, _resolve_variant


class SimpleComicRendererTests(unittest.TestCase):
    def test_ass_time_uses_centiseconds(self):
        self.assertEqual(_ass_time(0), "0:00:00.00")
        self.assertEqual(_ass_time(24), "0:00:01.00")

    def test_normalized_face_box_is_clamped(self):
        self.assertEqual(_box([-1, -1, 2, 2], 100, 80), (0, 0, 100, 80))

    def test_motion_manifest_is_optional_and_shot_indexed(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            self.assertEqual(_load_motion(project, None), {})
            manifest = project / "simple_comic_motion.json"
            manifest.write_text(json.dumps({"shots": [{"shot_id": "shot_01", "blink_frames": [3]}]}), encoding="utf-8")
            self.assertEqual(_load_motion(project, None)["shot_01"]["blink_frames"], [3])

    def test_variant_path_must_exist(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            self.assertIsNone(_resolve_variant(project, "shots/shot_01/motion/mouth_open.png"))
            target = project / "shots" / "shot_01" / "motion" / "mouth_open.png"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"png")
            self.assertEqual(_resolve_variant(project, target.relative_to(project).as_posix()), target)


if __name__ == "__main__":
    unittest.main()
