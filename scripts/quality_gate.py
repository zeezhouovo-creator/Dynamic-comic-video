"""Pre-preview quality gate for dynamic comic projects.

The gate reports structural and timing risks without pretending to replace visual
review. ``--autofix`` only repairs safe timeline metadata bounds.
"""
import argparse
import json
from pathlib import Path
import wave


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def issue(report, severity, category, shot, message, fix=None):
    item = {"severity": severity, "category": category, "shot": shot, "message": message}
    if fix:
        item["fix"] = fix
    report["issues"].append(item)


def audio_frames(path, fps):
    try:
        with wave.open(str(path), "rb") as stream:
            return round(stream.getnframes() / stream.getframerate() * fps)
    except (OSError, wave.Error):
        return None


def scan(project, autofix=False):
    project = Path(project).resolve()
    brief = read(project / "production_brief.json")
    chars = read(project / "characters.json")
    board = read(project / "storyboard.json")
    motion = read(project / "motion_plan.json")
    fps = brief["format"]["fps"]
    by_id = {shot["id"]: shot for shot in board["shots"]}
    report = {
        "version": "0.1",
        "project_id": brief["project_id"],
        "status": "PASS",
        "checks": {},
        "issues": [],
        "automatic_corrections": [],
        "requires_user_review": ["pixel-level identity, anatomy, seams, and acting naturalness"],
    }
    identities = {c["id"]: c.get("identity", {}) for c in chars.get("characters", [])}
    scenes = {scene["id"] for scene in board.get("scenes", [])}
    previous_tags = []
    action_counts = {}
    sequential = motion.get("version") == "0.3" or any(
        (item.get("performance") or {}).get("mode") == "sequential-comic" for item in motion.get("shots", [])
    )

    for shot in board["shots"]:
        sid = shot["id"]
        direction = shot.get("direction", {})
        if sequential and direction.get("scene_id") not in scenes:
            issue(report, "Critical", "scene_continuity", sid, "Shot references an unknown scene space")
        if sequential and shot.get("transition") != "cut":
            issue(report, "Critical", "cut", sid, "Dynamic comic shot must use a direct CUT")
        previous_tags.append((shot.get("shot_size"), shot.get("composition_tag"), shot.get("setting")))
        if len(previous_tags) >= 3 and len(set(previous_tags[-3:])) == 1:
            issue(report, "Minor", "repetition", sid, "Three consecutive shots repeat the same visual tags")

        dialogue = shot.get("dialogue", [])
        last_end = 0
        for cue in dialogue:
            start, end = cue["start_frame"], cue["end_frame"]
            if start < last_end or not 0 <= start < end <= shot["duration_frames"]:
                issue(report, "Major", "subtitle_sync", sid, "Dialogue interval is outside the shot or overlaps another cue")
            last_end = end
            if cue.get("audio"):
                audio_path = project / cue["audio"]
                if audio_path.is_file():
                    frames = audio_frames(audio_path, fps)
                    if frames is not None and frames > shot["duration_frames"]:
                        issue(report, "Major", "audio", sid, "Audio is longer than its shot duration")

        motion_shot = next((item for item in motion["shots"] if item["shot_id"] == sid), None)
        if not motion_shot:
            issue(report, "Critical", "timeline", sid, "Motion shot is missing")
            continue
        timeline = motion_shot.get("timeline")
        if timeline:
            if timeline.get("duration_frames") != shot["duration_frames"]:
                old = timeline.get("duration_frames")
                if autofix:
                    timeline["duration_frames"] = shot["duration_frames"]
                    report["automatic_corrections"].append({"shot": sid, "field": "timeline.duration_frames", "from": old, "to": shot["duration_frames"]})
                else:
                    issue(report, "Major", "timeline", sid, "Timeline duration does not match shot duration", "set to shot duration")
            if timeline.get("cut_at_frame", shot["duration_frames"]) > shot["duration_frames"]:
                if autofix:
                    old = timeline["cut_at_frame"]
                    timeline["cut_at_frame"] = shot["duration_frames"]
                    report["automatic_corrections"].append({"shot": sid, "field": "timeline.cut_at_frame", "from": old, "to": shot["duration_frames"]})
                else:
                    issue(report, "Major", "cut", sid, "CUT is later than the shot duration", "clamp to shot duration")
            for key in ("subtitle_events", "speech_intervals", "visual_events", "music_duck_events"):
                for event in timeline.get(key, []):
                    start = event.get("start_frame", 0)
                    end = event.get("end_frame", start + 1)
                    if start < 0 or end <= start or end > shot["duration_frames"]:
                        issue(report, "Major", "timeline", sid, f"{key} contains an out-of-bounds interval")

        actions = 0
        for layer in motion_shot.get("layers", []):
            acting = layer.get("acting", {})
            actions += len(acting.get("events", []))
            if acting.get("poses"):
                actions += max(0, len(acting["poses"]) - 2)
            if acting.get("speech") and not dialogue:
                issue(report, "Major", "mouth_sync", sid, "Mouth speech layer exists without dialogue timing")
            if motion_shot.get("performance", {}).get("mode") in ("sequential-comic", "fixed-camera-micro"):
                for key in ("from", "to"):
                    transform = layer.get(key, {})
                    if transform.get("x", 0) or transform.get("y", 0) or transform.get("scale", 1) != 1:
                        issue(report, "Major", "motion_naturalness", sid, "Fixed-camera shot contains whole-layer movement")
        action_counts[sid] = actions
        if actions > 2:
            issue(report, "Minor", "motion_density", sid, f"Shot contains {actions} acting events; ordinary dialogue usually needs 0–2")

    for cid, identity in identities.items():
        anchors = identity.get("distinctive_features") or identity.get("anchors")
        if not anchors:
            issue(report, "Major", "character_consistency", None, f"Character {cid} has no recorded identity anchors")

    categories = {
        "character_consistency": "角色一致性",
        "scene_continuity": "场景连续性",
        "motion_naturalness": "动作自然度",
        "mouth_sync": "嘴型同步",
        "subtitle_sync": "字幕同步",
        "audio": "音频",
        "cut": "CUT 节奏",
        "repetition": "重复构图",
        "motion_density": "动作密度",
        "timeline": "统一时间轴",
    }
    for key, label in categories.items():
        report["checks"][key] = "FIX" if any(i["category"] == key for i in report["issues"]) else "PASS"
    severities = [item["severity"] for item in report["issues"]]
    if "Critical" in severities:
        report["status"] = "BLOCKED"
    elif "Major" in severities:
        report["status"] = "FIX_REQUIRED"
    elif "Minor" in severities:
        report["status"] = "PASS_WITH_NOTES"
    report["summary"] = {"Critical": severities.count("Critical"), "Major": severities.count("Major"), "Minor": severities.count("Minor")}
    if autofix and report["automatic_corrections"]:
        save(project / "motion_plan.json", motion)
    save(project / "quality_report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--autofix", action="store_true")
    args = parser.parse_args()
    report = scan(args.project, args.autofix)
    print(json.dumps({"status": report["status"], "summary": report["summary"], "report": str((args.project / "quality_report.json").resolve())}, ensure_ascii=False))
    return 1 if report["status"] in ("BLOCKED", "FIX_REQUIRED") else 0


if __name__ == "__main__":
    raise SystemExit(main())
