"""Tests for the one-command preview orchestration."""
import unittest
from pathlib import Path
from unittest.mock import patch

from preview import review_points, run_preview, steps


class PreviewTests(unittest.TestCase):
    def test_steps_put_quality_gate_before_prepare_and_render(self):
        commands = steps(Path("C:/project"), Path("C:/renderer"))
        self.assertIn("validate", commands[0][0])
        self.assertIn("--autofix", commands[1][0])
        self.assertIn("validate", commands[2][0])
        self.assertIn("compile", commands[3][0])
        self.assertIn("prepare", commands[4][0])
        self.assertEqual(commands[-1][0][-2:], ["run", "render"])

    def test_steps_can_include_npm_install(self):
        commands = steps(Path("C:/project"), Path("C:/renderer"), install=True)
        self.assertEqual(commands[-2][0][-1], "ci")
        self.assertEqual(commands[-1][0][-2:], ["run", "render"])

    def test_steps_support_shot_preview_and_review_stills(self):
        points = [{"filename": "shot_001_first.png", "global_frame": 0}]
        commands = steps(Path("C:/project"), Path("C:/renderer"), shot="shot_001", stills=points)
        compile_command = next(command for command, _ in commands if "compile" in command)
        prepare_command = next(command for command, _ in commands if "prepare" in command)
        still_command = next(command for command, _ in commands if "still-frame" in command)
        self.assertEqual(compile_command[-2:], ["--shot", "shot_001"])
        self.assertEqual(prepare_command[-2:], ["--shot", "shot_001"])
        self.assertIn("out/visual-review/shot_001_first.png", still_command)
        self.assertIn("--frame=0", still_command)

    def test_review_points_use_local_frames_for_shot_preview(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / "motion_plan.json").write_text(json.dumps({"shots": [{
                "shot_id": "shot/001", "start_frame": 24, "duration_frames": 10,
            }]}), encoding="utf-8")
            full = review_points(project)
            local = review_points(project, "shot/001")
        self.assertEqual([item["global_frame"] for item in full], [24, 28, 33])
        self.assertEqual([item["global_frame"] for item in local], [0, 4, 9])
        self.assertEqual({item["filename"] for item in full}, {"shot_001_first.png", "shot_001_middle.png", "shot_001_last.png"})

    def test_run_preview_copies_rendered_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            renderer = root / "renderer"
            project.mkdir()
            renderer.mkdir()
            (project / "production_brief.json").write_text("{}", encoding="utf-8")
            rendered = renderer / "out"
            rendered.mkdir()
            (rendered / "video.mp4").write_bytes(b"preview")
            with patch("preview.subprocess.run") as run:
                destination = run_preview(project, renderer)
            self.assertEqual(destination, project / "preview.mp4")
            self.assertEqual(destination.read_bytes(), b"preview")
            self.assertEqual(run.call_count, len(steps(project, renderer)))

    def test_shot_preview_copies_visual_review_artifacts(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            renderer = root / "renderer"
            project.mkdir()
            renderer.mkdir()
            (project / "production_brief.json").write_text("{}", encoding="utf-8")
            (project / "motion_plan.json").write_text(json.dumps({"shots": [{
                "shot_id": "shot/001", "start_frame": 12, "duration_frames": 6,
            }]}), encoding="utf-8")
            rendered = renderer / "out"
            review = rendered / "visual-review"
            review.mkdir(parents=True)
            (rendered / "video.mp4").write_bytes(b"preview")
            for position in ("first", "middle", "last"):
                (review / f"shot_001_{position}.png").write_bytes(position.encode())
            with patch("preview.subprocess.run") as run:
                destination = run_preview(project, renderer, shot="shot/001")
            self.assertEqual(destination, project / "preview_shot_001.mp4")
            manifest = json.loads((project / "visual_review.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], "0.2")
            self.assertEqual(manifest["scope"]["shot"], "shot/001")
            self.assertEqual(len(manifest["frames"]), 3)
            self.assertTrue(manifest["source_fingerprint"])
            self.assertTrue(manifest["preview_sha256"])
            self.assertTrue(all(frame["sha256"] for frame in manifest["frames"]))
            self.assertTrue(all(not frame["reviewed"] for frame in manifest["frames"]))
            self.assertEqual(run.call_count, len(steps(project, renderer, shot="shot/001", stills=review_points(project, "shot/001"))))


if __name__ == "__main__":
    unittest.main()
