"""Tests for the local environment diagnostic command."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from doctor import _renderer_check, diagnose, parse_version


class DoctorTests(unittest.TestCase):
    def test_parse_version_accepts_node_style_output(self):
        self.assertEqual(parse_version("v20.11.1"), (20, 11, 1))
        self.assertEqual(parse_version("npm 11.16.0"), (11, 16, 0))
        self.assertIsNone(parse_version("unknown"))

    def test_renderer_check_requires_remotion_and_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            renderer = Path(temp)
            (renderer / "package.json").write_text(json.dumps({"dependencies": {"remotion": "4.0.0"}}), encoding="utf-8")
            result = _renderer_check(renderer)
            self.assertEqual(result["status"], "FAIL")
            (renderer / "node_modules").mkdir()
            self.assertEqual(_renderer_check(renderer)["status"], "PASS")

    def test_diagnose_returns_structured_checks(self):
        with patch("doctor._command_version", side_effect=[((20, 0, 0), "v20.0.0"), ((10, 0, 0), "10.0.0")]), patch("doctor._renderer_check", return_value={"name": "renderer", "status": "PASS", "detail": "ok"}):
            result = diagnose()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["failed"], 0)
        self.assertTrue(any(item["name"] == "python" for item in result["checks"]))


if __name__ == "__main__":
    unittest.main()
