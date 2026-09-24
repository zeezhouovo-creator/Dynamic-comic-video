"""Persist and route the V1.0 dynamic-comic project state machine."""
import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

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

FINGERPRINT_FILES = (
    "production_brief.json",
    "characters.json",
    "storyboard.json",
    "motion_plan.json",
    "asset_report.json",
    "quality_report.json",
)

def state_path(project):
    return Path(project).resolve() / "project_state.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_fingerprint(project):
    """Hash the production inputs that make a preview reviewable."""
    root = Path(project).resolve()
    digest = hashlib.sha256()
    for name in FINGERPRINT_FILES:
        path = root / name
        digest.update(name.encode("utf-8"))
        if path.is_file():
            digest.update(bytes((0,)))
            digest.update(path.read_bytes())
        else:
            digest.update(bytes((1,)))
    return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _schema_errors(name, data):
    """Return readable contract errors for one production JSON document."""
    schema = read(ROOT / "schemas" / f"{name}.schema.json")
    Draft202012Validator.check_schema(schema)
    errors = []
    for error in Draft202012Validator(schema).iter_errors(data):
        location = f"{name}.json"
        for part in error.absolute_path:
            location += f"[{part}]" if isinstance(part, int) else f".{part}"
        errors.append(f"{location}: {error.message}")
    return sorted(errors)


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


REVISION_STATUSES = ("open", "in_progress", "resolved", "wont_fix")


def revision_log_path(project):
    return Path(project).resolve() / "revision_log.json"


def _read_revision_log(project):
    path = revision_log_path(project)
    if not path.is_file():
        return {"version": "0.1", "project_id": Path(project).resolve().name, "entries": []}
    try:
        data = read(path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("revision_log.json is not valid JSON") from error
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise ValueError("revision_log.json must contain an entries array")
    return data


def open_revision_entries(project):
    """Return open revision entries and a readable log error, if any."""
    try:
        data = _read_revision_log(project)
    except ValueError as error:
        return [], str(error)
    entries = [
        item for item in data["entries"]
        if isinstance(item, dict) and item.get("status") in ("open", "in_progress")
    ]
    return entries, None


def record_revision(project, text, state=None, module=None, shot=None, status="open", note=None):
    """Append a routed feedback item to the local revision ledger."""
    if status not in REVISION_STATUSES:
        raise ValueError(f"Unknown revision status: {status}")
    root = Path(project).resolve()
    route = route_feedback(text)
    data = _read_revision_log(root)
    existing_ids = {item.get("id") for item in data["entries"] if isinstance(item, dict)}
    index = len(data["entries"]) + 1
    entry_id = f"rev_{index:03d}"
    while entry_id in existing_ids:
        index += 1
        entry_id = f"rev_{index:03d}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    entry = {
        "id": entry_id,
        "created_at": now,
        "updated_at": now,
        "status": status,
        "feedback": text,
        "state": state or route["state"],
        "module": module or route["module"],
        "shot": shot,
        "source_fingerprint": source_fingerprint(root),
    }
    if note:
        entry["note"] = note
    data["entries"].append(entry)
    write(revision_log_path(root), data)
    return entry


def update_revision(project, entry_id, status, note=None):
    """Update one revision entry without changing its original feedback."""
    if status not in REVISION_STATUSES:
        raise ValueError(f"Unknown revision status: {status}")
    root = Path(project).resolve()
    data = _read_revision_log(root)
    entry = next((item for item in data["entries"] if isinstance(item, dict) and item.get("id") == entry_id), None)
    if entry is None:
        raise ValueError(f"Unknown revision id: {entry_id}")
    entry["status"] = status
    entry["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if note is not None:
        entry["note"] = note
    if status in ("resolved", "wont_fix"):
        entry["resolved_at"] = entry["updated_at"]
    write(revision_log_path(root), data)
    return entry


def _resolve_preview_reference(root, reference):
    try:
        path = Path(reference)
    except (TypeError, ValueError):
        return None
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _safe_review_image(root, reference):
    try:
        path = (root / Path(reference)).resolve()
        path.relative_to(root)
        return path
    except (OSError, TypeError, ValueError):
        return None


def _read_visual_review(review_path):
    try:
        data = read(review_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _visual_review_freshness_issues(root, data):
    """Check that a review manifest still points at the current local artifacts."""
    issues = []
    if data.get("source_fingerprint") != source_fingerprint(root):
        issues.append("visual review source fingerprint is stale")
    preview_reference = data.get("preview")
    preview_path = _resolve_preview_reference(root, preview_reference) if preview_reference else None
    if preview_path is None or not preview_path.is_file():
        issues.append("visual review preview file")
    elif data.get("preview_sha256") != file_sha256(preview_path):
        issues.append("visual review preview fingerprint is stale")
    frames = data.get("frames")
    if not isinstance(frames, list) or not frames:
        issues.append("visual review frames")
        return issues
    for frame in frames:
        if not isinstance(frame, dict) or not frame.get("image"):
            issues.append("valid visual review frame entries")
            continue
        image_path = _safe_review_image(root, frame["image"])
        if image_path is None:
            issues.append(f"safe visual review image path: {frame.get('image')}")
        elif not image_path.is_file():
            issues.append(f"visual review image: {frame['image']}")
        elif frame.get("sha256") != file_sha256(image_path):
            issues.append(f"visual review frame fingerprint is stale: {frame.get('shot_id', '?')} {frame.get('position', '?')}")
    return issues


def review(project, approved=False, note=None, reviewer=None):
    """Record a human visual-review decision for the current preview."""
    root = Path(project).resolve()
    path = root / "visual_review.json"
    if not path.is_file():
        raise ValueError(f"Missing visual review manifest: {path}")
    data = _read_visual_review(path)
    if data is None:
        raise ValueError("visual_review.json must contain a JSON object")
    if approved:
        freshness = _visual_review_freshness_issues(root, data)
        if freshness:
            raise ValueError("Cannot approve stale visual review: " + "; ".join(freshness))
        for frame in data["frames"]:
            frame["reviewed"] = True
        data["review_status"] = "approved"
        for revision_id in data.get("supersedes_revisions", []):
            try:
                update_revision(root, revision_id, "resolved", "Resolved by approved visual review")
            except ValueError:
                pass
    else:
        data["review_status"] = "rejected"
        for frame in data.get("frames", []):
            if isinstance(frame, dict):
                frame["reviewed"] = False
        revision = record_revision(
            root,
            note or "Visual review rejected",
            state="REVISION",
            module="visual_review",
            status="open",
        )
        data["revision_id"] = revision["id"]
    if note:
        data["review_notes"] = note
    data["reviewed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if reviewer:
        data["reviewer"] = reviewer
    write(path, data)
    return data


def _asset_report_issues(root, report_path):
    """Return machine-checkable asset report issues without trusting its summary."""
    if not report_path.is_file():
        return None, []
    try:
        data = read(report_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None, ["valid asset_report.json"]
    if not isinstance(data, dict):
        return data, ["valid asset_report.json"]
    shots = data.get("shots")
    if not isinstance(shots, list):
        return data, ["valid asset_report.json shots"]
    issues = []
    changed = []
    missing = []
    for item in shots:
        if not isinstance(item, dict) or not item.get("shot_id"):
            issues.append("valid asset_report.json shot entries")
            continue
        shot_id = item["shot_id"]
        if item.get("changed"):
            changed.append(shot_id)
        for path in item.get("missing", []) or []:
            missing.append(f"{shot_id}: {path}")
    if missing:
        issues.append("missing assets: " + ", ".join(missing))
    if changed:
        issues.append("asset fingerprint review: " + ", ".join(changed))
    return data, issues


def _visual_review_issues(root, review_path, preview_path=None, data=None):
    """Check that the generated visual review manifest still matches the preview."""
    if not review_path.is_file():
        return ["visual_review.json"]
    data = data if data is not None else _read_visual_review(review_path)
    if data is None:
        return ["valid visual_review.json"]
    issues = _visual_review_freshness_issues(root, data)
    if not data.get("preview"):
        issues.append("visual review preview reference")
    if isinstance(data.get("frames"), list):
        for frame in data["frames"]:
            if isinstance(frame, dict) and not frame.get("reviewed"):
                issues.append(f"review frame not checked: {frame.get('shot_id', '?')} {frame.get('position', '?')}")
    if data.get("review_status") != "approved":
        issues.append("visual_review.json review_status=approved")
    if preview_path and data.get("preview"):
        referenced = _resolve_preview_reference(root, data["preview"])
        if referenced is not None and referenced != preview_path.resolve():
            issues.append("visual review matches current preview")
    return issues


def inspect(project):
    """Suggest the next workflow state from observable project files only."""
    root = Path(project).resolve()
    evidence = []
    missing = []
    brief = root / "production_brief.json"
    chars = root / "characters.json"
    board = root / "storyboard.json"
    motion = root / "motion_plan.json"
    assets = root / "asset_report.json"
    report = root / "quality_report.json"
    visual_review = root / "visual_review.json"
    previews = list(root.glob("*.mp4")) + list(root.glob("**/out/*.mp4"))
    if not brief.is_file():
        return {"suggested_state": "INIT", "confidence": "high", "evidence": [], "missing": ["production_brief.json"]}
    evidence.append("production_brief.json")
    try:
        brief_data = read(brief)
        if not isinstance(brief_data, dict) or not brief_data.get("project_id"):
            return {"suggested_state": "INIT", "confidence": "high", "evidence": evidence, "missing": ["valid production_brief.json"]}
        schema_errors = _schema_errors("production_brief", brief_data)
        if schema_errors:
            return {"suggested_state": "INIT", "confidence": "high", "evidence": evidence, "missing": schema_errors, "schema_errors": schema_errors}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"suggested_state": "INIT", "confidence": "high", "evidence": evidence, "missing": ["valid production_brief.json"]}
    if not chars.is_file():
        return {"suggested_state": "CHARACTER", "confidence": "high", "evidence": evidence, "missing": ["characters.json"]}
    evidence.append("characters.json")
    try:
        character_data = read(chars)
        if not isinstance(character_data, dict) or not isinstance(character_data.get("characters"), list):
            return {"suggested_state": "CHARACTER", "confidence": "high", "evidence": evidence, "missing": ["valid characters.json"]}
        schema_errors = _schema_errors("characters", character_data)
        if schema_errors:
            return {"suggested_state": "CHARACTER", "confidence": "high", "evidence": evidence, "missing": schema_errors, "schema_errors": schema_errors}
        if any(
            not isinstance(item, dict)
            or not isinstance(item.get("reference"), dict)
            or item.get("reference", {}).get("status") != "ready"
            for item in character_data.get("characters", [])
        ):
            return {"suggested_state": "CHARACTER", "confidence": "high", "evidence": evidence, "missing": ["ready character references"]}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"suggested_state": "CHARACTER", "confidence": "high", "evidence": evidence, "missing": ["valid characters.json"]}
    if not board.is_file():
        return {"suggested_state": "STORYBOARD", "confidence": "high", "evidence": evidence, "missing": ["storyboard.json"]}
    evidence.append("storyboard.json")
    try:
        board_data = read(board)
        if not isinstance(board_data, dict) or not isinstance(board_data.get("shots"), list):
            return {"suggested_state": "STORYBOARD", "confidence": "high", "evidence": evidence, "missing": ["valid storyboard.json"]}
        schema_errors = _schema_errors("storyboard", board_data)
        if schema_errors:
            return {"suggested_state": "STORYBOARD", "confidence": "high", "evidence": evidence, "missing": schema_errors, "schema_errors": schema_errors}
        shots = board_data.get("shots", [])
        if not shots:
            return {"suggested_state": "STORYBOARD", "confidence": "high", "evidence": evidence, "missing": ["storyboard shots"]}
        if any(not isinstance(item, dict) or not item.get("direction") for item in shots):
            return {"suggested_state": "STORYBOARD", "confidence": "high", "evidence": evidence, "missing": ["independent shot direction"]}
        if any(
            not isinstance(item.get("dialogue", []), list)
            or any(not isinstance(cue, dict) for cue in item.get("dialogue", []))
            for item in shots
        ):
            return {"suggested_state": "STORYBOARD", "confidence": "high", "evidence": evidence, "missing": ["valid storyboard dialogue entries"]}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"suggested_state": "STORYBOARD", "confidence": "high", "evidence": evidence, "missing": ["valid storyboard.json"]}
    if not motion.is_file():
        return {"suggested_state": "ANIMATION", "confidence": "high", "evidence": evidence, "missing": ["motion_plan.json"]}
    evidence.append("motion_plan.json")
    try:
        motion_data = read(motion)
        if (
            not isinstance(motion_data, dict)
            or not isinstance(motion_data.get("shots", []), list)
            or any(not isinstance(item, dict) for item in motion_data.get("shots", []))
        ):
            return {"suggested_state": "ANIMATION", "confidence": "high", "evidence": evidence, "missing": ["valid motion_plan.json"]}
        schema_errors = _schema_errors("motion_plan", motion_data)
        if schema_errors:
            return {"suggested_state": "ANIMATION", "confidence": "high", "evidence": evidence, "missing": schema_errors, "schema_errors": schema_errors}
        dialogue_audio = [cue.get("audio") for item in board_data.get("shots", []) for cue in item.get("dialogue", []) if cue.get("audio")]
        missing_audio = [name for name in dialogue_audio if not (root / name).is_file()]
        if missing_audio:
            return {"suggested_state": "AUDIO", "confidence": "high", "evidence": evidence, "missing": missing_audio}
        if motion_data.get("asset_mode") == "production" and not all(item.get("review", {}).get("master_alignment") for item in motion_data.get("shots", [])):
            return {"suggested_state": "QUALITY_CHECK", "confidence": "medium", "evidence": evidence, "missing": ["master visual review"]}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"suggested_state": "ANIMATION", "confidence": "high", "evidence": evidence, "missing": ["valid motion_plan.json"]}
    if assets.is_file():
        asset_data, asset_issues = _asset_report_issues(root, assets)
        evidence.append("asset_report.json")
        if asset_issues:
            if asset_data is None or any(item.startswith("valid asset_report") for item in asset_issues):
                return {"suggested_state": "ANIMATION", "confidence": "high", "evidence": evidence, "missing": asset_issues}
            if any(item.startswith("missing assets:") for item in asset_issues):
                return {"suggested_state": "ANIMATION", "confidence": "high", "evidence": evidence, "missing": asset_issues}
            return {"suggested_state": "ANIMATION", "confidence": "medium", "evidence": evidence, "missing": asset_issues}
    open_revisions, revision_error = open_revision_entries(root)
    if revision_error:
        evidence.append("revision_log.json")
        return {"suggested_state": "REVISION", "confidence": "high", "evidence": evidence, "missing": [revision_error]}
    if open_revisions:
        evidence.append("revision_log.json")
        return {
            "suggested_state": "REVISION",
            "confidence": "high",
            "evidence": evidence,
            "missing": [f"{item.get('id', 'revision')}: {item.get('feedback', 'open revision')}" for item in open_revisions],
            "revisions": open_revisions,
        }
    if not report.is_file():
        return {"suggested_state": "QUALITY_CHECK", "confidence": "medium", "evidence": evidence, "missing": ["quality_report.json"]}
    evidence.append("quality_report.json")
    try:
        report_data = read(report)
        if not isinstance(report_data, dict) or report_data.get("status") not in ("PASS", "PASS_WITH_NOTES", "BLOCKED", "FIX_REQUIRED"):
            return {"suggested_state": "QUALITY_CHECK", "confidence": "high", "evidence": evidence, "missing": ["valid quality_report.json"]}
        if report_data.get("status") in ("BLOCKED", "FIX_REQUIRED"):
            return {"suggested_state": "REVISION", "confidence": "high", "evidence": evidence, "missing": ["quality gate fixes"]}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"suggested_state": "QUALITY_CHECK", "confidence": "high", "evidence": evidence, "missing": ["valid quality_report.json"]}
    if not previews:
        return {"suggested_state": "COMPOSITION", "confidence": "medium", "evidence": evidence, "missing": ["preview MP4"]}
    evidence.append("preview MP4")
    review_data = _read_visual_review(visual_review) if visual_review.is_file() else None
    current_preview = None
    if review_data and review_data.get("preview"):
        referenced = _resolve_preview_reference(root, review_data["preview"])
        if referenced and referenced.is_file():
            current_preview = referenced
    if current_preview is None:
        current_preview = next((path for path in previews if path.parent == root), None)
    if review_data and review_data.get("review_status") in ("rejected", "changes_requested"):
        note = review_data.get("review_notes") or "visual review rejected"
        if visual_review.is_file():
            evidence.append("visual_review.json")
        return {"suggested_state": "REVISION", "confidence": "high", "evidence": evidence, "missing": [note]}
    review_issues = _visual_review_issues(root, visual_review, current_preview, review_data)
    if review_issues:
        if visual_review.is_file():
            evidence.append("visual_review.json")
        return {"suggested_state": "PREVIEW", "confidence": "high", "evidence": evidence, "missing": review_issues + ["FINAL is never inferred"]}
    evidence.append("visual_review.json")
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
    p_review = sub.add_parser("review")
    p_review.add_argument("project", type=Path)
    review_group = p_review.add_mutually_exclusive_group(required=True)
    review_group.add_argument("--approve", action="store_true")
    review_group.add_argument("--reject", action="store_true")
    p_review.add_argument("--note")
    p_review.add_argument("--reviewer")
    p_revision = sub.add_parser("revision")
    revision_sub = p_revision.add_subparsers(dest="revision_command", required=True)
    p_revision_add = revision_sub.add_parser("add")
    p_revision_add.add_argument("project", type=Path)
    p_revision_add.add_argument("--text", required=True)
    p_revision_add.add_argument("--state", choices=STATES)
    p_revision_add.add_argument("--module")
    p_revision_add.add_argument("--shot")
    p_revision_add.add_argument("--status", choices=REVISION_STATUSES, default="open")
    p_revision_add.add_argument("--note")
    p_revision_update = revision_sub.add_parser("update")
    p_revision_update.add_argument("project", type=Path)
    p_revision_update.add_argument("entry_id")
    p_revision_update.add_argument("--status", choices=REVISION_STATUSES, required=True)
    p_revision_update.add_argument("--note")
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
    elif args.command == "review":
        value = review(args.project, approved=args.approve, note=args.note, reviewer=args.reviewer)
    elif args.command == "revision":
        if args.revision_command == "add":
            value = record_revision(args.project, args.text, args.state, args.module, args.shot, args.status, args.note)
        else:
            value = update_revision(args.project, args.entry_id, args.status, args.note)
    else:
        value = inspect(args.project)
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
