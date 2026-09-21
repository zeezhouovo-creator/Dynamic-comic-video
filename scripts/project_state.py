"""Persist and route the V1.0 dynamic-comic project state machine."""
import argparse
import json
import sys
from pathlib import Path

STATES = ("INIT", "CHARACTER", "STORY", "STORYBOARD", "ANIMATION", "AUDIO", "PERFORMANCE", "COMPOSITION", "QUALITY_CHECK", "PREVIEW", "REVISION", "FINAL")
TRANSITIONS = {
    "INIT": {"CHARACTER", "STORY", "STORYBOARD"},
    "CHARACTER": {"STORY", "STORYBOARD", "REVISION"},
    "STORY": {"CHARACTER", "STORYBOARD", "REVISION"},
    "STORYBOARD": {"ANIMATION", "STORY", "REVISION"},
    "ANIMATION": {"AUDIO", "STORYBOARD", "REVISION"},
    "AUDIO": {"PERFORMANCE", "ANIMATION", "REVISION"},
    "PERFORMANCE": {"COMPOSITION", "AUDIO", "REVISION"},
    "COMPOSITION": {"QUALITY_CHECK", "PERFORMANCE", "REVISION"},
    "QUALITY_CHECK": {"PREVIEW", "COMPOSITION", "REVISION"},
    "PREVIEW": {"FINAL", "REVISION", "QUALITY_CHECK"},
    "REVISION": set(STATES) - {"INIT", "FINAL"},
    "FINAL": {"REVISION"},
}

FEEDBACK_ROUTES = (
    (("不像同一个人", "变脸", "发型", "五官", "服装"), "CHARACTER", "character_consistency"),
    (("动作", "僵", "晃", "漂浮", "一直动"), "ANIMATION", "motion_naturalness"),
    (("嘴", "音画", "配音", "声音", "听不清"), "AUDIO", "audio_timeline"),
    (("字幕", "字太大", "字太快", "字幕遮挡"), "AUDIO", "subtitle_sync"),
    (("特效", "音效", "太热闹"), "PERFORMANCE", "comic_feedback"),
    (("背景", "场景", "空间跳", "像换地方"), "STORYBOARD", "scene_continuity"),
    (("像PPT", "图片轮播"), "STORYBOARD", "shot_continuity"),
    (("太赶", "太拖", "节奏", "停顿"), "QUALITY_CHECK", "timing_and_cut"),
)


def state_path(project):
    return Path(project).resolve() / "project_state.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def init(project, project_id=None):
    path = state_path(project)
    if path.exists():
        raise ValueError(f"State already exists: {path}")
    project_id = project_id or Path(project).resolve().name
    value = {"version": "0.1", "project_id": project_id, "state": "INIT", "pending": [], "history": []}
    write(path, value)
    return value


def transition(project, target, reason, pending=None):
    if target not in STATES:
        raise ValueError(f"Unknown state: {target}")
    path = state_path(project)
    value = read(path)
    current = value["state"]
    if target not in TRANSITIONS[current] and target != current:
        raise ValueError(f"Invalid transition {current} -> {target}")
    if target != current:
        value["history"].append({"from": current, "to": target, "reason": reason})
    value["state"] = target
    if pending is not None:
        value["pending"] = pending
    write(path, value)
    return value


def route_feedback(text):
    lowered = text.lower()
    for keywords, state, module in FEEDBACK_ROUTES:
        if any(keyword.lower() in lowered for keyword in keywords):
            return {"state": state, "module": module, "text": text}
    return {"state": "REVISION", "module": "manual_review", "text": text}


def inspect(project):
    """Suggest the next workflow state from observable project files only."""
    root = Path(project).resolve()
    evidence = []
    missing = []
    brief = root / "production_brief.json"
    chars = root / "characters.json"
    board = root / "storyboard.json"
    motion = root / "motion_plan.json"
    report = root / "quality_report.json"
    previews = list(root.glob("*.mp4")) + list(root.glob("**/out/*.mp4"))
    if not brief.is_file():
        return {"suggested_state": "INIT", "confidence": "high", "evidence": [], "missing": ["production_brief.json"]}
    evidence.append("production_brief.json")
    if not chars.is_file():
        return {"suggested_state": "CHARACTER", "confidence": "high", "evidence": evidence, "missing": ["characters.json"]}
    evidence.append("characters.json")
    try:
        character_data = read(chars)
        if any(item.get("reference", {}).get("status") != "ready" for item in character_data.get("characters", [])):
            return {"suggested_state": "CHARACTER", "confidence": "high", "evidence": evidence, "missing": ["ready character references"]}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"suggested_state": "CHARACTER", "confidence": "high", "evidence": evidence, "missing": ["valid characters.json"]}
    if not board.is_file():
        return {"suggested_state": "STORYBOARD", "confidence": "high", "evidence": evidence, "missing": ["storyboard.json"]}
    evidence.append("storyboard.json")
    try:
        board_data = read(board)
        shots = board_data.get("shots", [])
        if not shots:
            return {"suggested_state": "STORYBOARD", "confidence": "high", "evidence": evidence, "missing": ["storyboard shots"]}
        if any(not item.get("direction") for item in shots):
            return {"suggested_state": "STORYBOARD", "confidence": "high", "evidence": evidence, "missing": ["independent shot direction"]}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"suggested_state": "STORYBOARD", "confidence": "high", "evidence": evidence, "missing": ["valid storyboard.json"]}
    if not motion.is_file():
        return {"suggested_state": "ANIMATION", "confidence": "high", "evidence": evidence, "missing": ["motion_plan.json"]}
    evidence.append("motion_plan.json")
    try:
        motion_data = read(motion)
        dialogue_audio = [cue.get("audio") for item in board_data.get("shots", []) for cue in item.get("dialogue", []) if cue.get("audio")]
        missing_audio = [name for name in dialogue_audio if not (root / name).is_file()]
        if missing_audio:
            return {"suggested_state": "AUDIO", "confidence": "high", "evidence": evidence, "missing": missing_audio}
        if motion_data.get("asset_mode") == "production" and not all(item.get("review", {}).get("master_alignment") for item in motion_data.get("shots", [])):
            return {"suggested_state": "QUALITY_CHECK", "confidence": "medium", "evidence": evidence, "missing": ["master visual review"]}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"suggested_state": "ANIMATION", "confidence": "high", "evidence": evidence, "missing": ["valid motion_plan.json"]}
    if not report.is_file():
        return {"suggested_state": "QUALITY_CHECK", "confidence": "medium", "evidence": evidence, "missing": ["quality_report.json"]}
    evidence.append("quality_report.json")
    try:
        report_data = read(report)
        if report_data.get("status") in ("BLOCKED", "FIX_REQUIRED"):
            return {"suggested_state": "REVISION", "confidence": "high", "evidence": evidence, "missing": ["quality gate fixes"]}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"suggested_state": "QUALITY_CHECK", "confidence": "high", "evidence": evidence, "missing": ["valid quality_report.json"]}
    if not previews:
        return {"suggested_state": "COMPOSITION", "confidence": "medium", "evidence": evidence, "missing": ["preview MP4"]}
    evidence.append("preview MP4")
    return {"suggested_state": "PREVIEW", "confidence": "medium", "evidence": evidence, "missing": ["user review; FINAL is never inferred"]}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Dynamic Comic V1.0 project state helper")
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("project", type=Path)
    p_init.add_argument("--project-id")
    p_show = sub.add_parser("show")
    p_show.add_argument("project", type=Path)
    p_transition = sub.add_parser("transition")
    p_transition.add_argument("project", type=Path)
    p_transition.add_argument("state", choices=STATES)
    p_transition.add_argument("--reason", required=True)
    p_transition.add_argument("--pending", nargs="*", default=None)
    p_feedback = sub.add_parser("route-feedback")
    p_feedback.add_argument("text")
    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("project", type=Path)
    args = parser.parse_args()
    if args.command == "init":
        value = init(args.project, args.project_id)
    elif args.command == "show":
        value = read(state_path(args.project))
    elif args.command == "transition":
        value = transition(args.project, args.state, args.reason, args.pending)
    elif args.command == "route-feedback":
        value = route_feedback(args.text)
    else:
        value = inspect(args.project)
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
