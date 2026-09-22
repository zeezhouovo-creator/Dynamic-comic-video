"""Tests for the one-command preview orchestration."""
import unittest
from pathlib import Path
from unittest.mock import patch

from preview import run_preview, steps


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


if __name__ == "__main__":
    unittest.main()
