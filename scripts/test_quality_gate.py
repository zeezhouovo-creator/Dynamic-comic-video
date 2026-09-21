"""Regression tests for the pre-preview timeline quality gate."""
import tempfile
import unittest
from pathlib import Path

from make_dialogue_fixture import build_dialogue
from pipeline import read, save
from quality_gate import scan


class QualityGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = build_dialogue(Path(self.temp.name) / "project")
        motion = read(self.project / "motion_plan.json")
        board = read(self.project / "storyboard.json")
        for shot, board_shot in zip(motion["shots"], board["shots"]):
            cue = board_shot["dialogue"][0]
            shot["timeline"] = {
                "scene_id": "test-room",
                "duration_frames": shot["duration_frames"],
                "audio": cue["audio"],
                "audio_start_frame": cue["start_frame"],
                "subtitle_events": [{"start_frame": cue["start_frame"], "end_frame": cue["end_frame"], "text": cue["text"]}],
                "speech_intervals": [{"start_frame": cue["start_frame"], "end_frame": cue["end_frame"], "speaker": cue["speaker"]}],
                "action_events": [{"event_id": "gesture", "trigger": "speech", "start_frame": 6, "peak_frame": 12, "settle_frame": 16, "end_frame": 20, "description": "one event-driven gesture"}],
                "expression_events": [],
                "blink_events": [{"frame": 24, "description": "one blink"}],
                "sound_events": [],
                "cut_at_frame": shot["duration_frames"],
            }
        save(self.project / "motion_plan.json", motion)

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_event_phases_pass(self):
        self.assertEqual(scan(self.project)["summary"], {"Critical": 0, "Major": 0, "Minor": 0})

    def test_event_phase_order_is_reported(self):
        motion = read(self.project / "motion_plan.json")
        motion["shots"][0]["timeline"]["action_events"][0]["peak_frame"] = 5
        save(self.project / "motion_plan.json", motion)
        report = scan(self.project)
        self.assertTrue(any("event phases out of order" in item["message"] for item in report["issues"]))

    def test_blink_bounds_are_reported(self):
        motion = read(self.project / "motion_plan.json")
        motion["shots"][0]["timeline"]["blink_events"][0]["frame"] = 999
        save(self.project / "motion_plan.json", motion)
        report = scan(self.project)
        self.assertTrue(any("blink_events" in item["message"] for item in report["issues"]))

    def test_negative_cut_is_not_autofixed(self):
        motion = read(self.project / "motion_plan.json")
        motion["shots"][0]["timeline"]["cut_at_frame"] = -1
        save(self.project / "motion_plan.json", motion)
        report = scan(self.project, autofix=True)
        self.assertTrue(any(item["category"] == "cut" and "before" in item["message"] for item in report["issues"]))


if __name__ == "__main__":
    unittest.main()
