"""Tests for the local delivery gate."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from deliver import check
from project_state import file_sha256, source_fingerprint


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        source = Path(__file__).resolve().parents[1] / "examples" / "library"
        shutil.copytree(source, self.project)
        characters = json.loads((self.project / "characters.json").read_text(encoding="utf-8"))
        characters["characters"][0]["reference"]["status"] = "ready"
        (self.project / "characters.json").write_text(json.dumps(characters, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, value):
        (self.project / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def seed_review(self):
        (self.project / "quality_report.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
        preview = self.project / "preview.mp4"
        preview.write_bytes(b"fake-mp4")
        image = self.project / "review.png"
        image.write_bytes(b"frame")
        self.write("visual_review.json", {
            "version": "0.2",
            "preview": "preview.mp4",
            "preview_sha256": file_sha256(preview),
            "source_fingerprint": source_fingerprint(self.project),
            "frames": [{
                "shot_id": "shot_001",
                "position": "first",
                "image": "review.png",
                "sha256": file_sha256(image),
                "reviewed": True,
            }],
            "review_status": "approved",
        })

    def test_missing_evidence_is_saved_as_a_failed_report(self):
        report = check(self.project)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue((self.project / "delivery_report.json").is_file())
        self.assertIn("quality_gate", " ".join(report["blocking_issues"]))

    def test_open_revision_blocks_delivery(self):
        self.seed_review()
        self.write("revision_log.json", {
            "version": "0.1",
            "project_id": "library",
            "entries": [{"id": "rev_001", "status": "open", "feedback": "动作太僵"}],
        })
        with patch("deliver._probe_media", return_value={"width": 960, "height": 540, "fps": 24.0, "duration_seconds": 6.0}):
            report = check(self.project)
        self.assertEqual(report["status"], "FAIL")
        revisions = next(item for item in report["checks"] if item["name"] == "revisions")
        self.assertEqual(revisions["status"], "FAIL")

    def test_contract_error_blocks_delivery(self):
        self.seed_review()
        brief = json.loads((self.project / "production_brief.json").read_text(encoding="utf-8"))
        brief["format"]["width"] = "960"
        (self.project / "production_brief.json").write_text(json.dumps(brief), encoding="utf-8")
        report = check(self.project)
        contracts = next(item for item in report["checks"] if item["name"] == "contracts")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(contracts["status"], "FAIL")

    def test_approved_review_and_playable_media_pass(self):
        self.seed_review()
        with patch("deliver._probe_media", return_value={"width": 960, "height": 540, "fps": 24.0, "duration_seconds": 6.0}):
            report = check(self.project)
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["source_fingerprint"])
        media = next(item for item in report["checks"] if item["name"] == "media")
        self.assertEqual(media["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
