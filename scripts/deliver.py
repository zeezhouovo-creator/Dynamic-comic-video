"""Run the local delivery gate for a dynamic-comic project.

The gate combines contract validation, the pre-preview quality report, human
visual review evidence, the revision ledger, and a local ffprobe inspection of
the final MP4.  It never installs packages, uploads files, or changes project
inputs.  A report is written even when delivery is blocked so the next action
is explicit and repeatable.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from pipeline import validate
from project_state import (
    _read_visual_review,
    _resolve_preview_reference,
    _visual_review_issues,
    file_sha256,
    open_revision_entries,
    source_fingerprint,
)


PASS_QUALITY_STATUSES = {"PASS", "PASS_WITH_NOTES"}


def _which(command):
    """Resolve a local executable on Windows and POSIX without shell lookup."""
    names = [command]
    if os.name == "nt":
        names.extend([f"{command}.exe", f"{command}.cmd"])
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _fps(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and "/" in value:
        numerator, denominator = value.split("/", 1)
        try:
            return float(numerator) / float(denominator)
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _probe_media(path):
    """Read the playable video stream metadata with the local ffprobe binary."""
    command = _which("ffprobe")
    if not command:
        raise RuntimeError("ffprobe is required to prove that the delivery MP4 is playable")
    result = subprocess.run(
        [
            command,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,width,height,avg_frame_rate:format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or "ffprobe failed").strip()
        raise RuntimeError(message)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("ffprobe returned invalid JSON") from error
    streams = [item for item in data.get("streams", []) if item.get("codec_type") == "video"]
    if not streams:
        raise RuntimeError("MP4 contains no video stream")
    stream = streams[0]
    duration = (data.get("format") or {}).get("duration")
    try:
        duration = float(duration)
    except (TypeError, ValueError):
        duration = None
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "fps": _fps(stream.get("avg_frame_rate")),
        "duration_seconds": duration,
    }


def _check_contracts(root):
    try:
        data, errors, warnings = validate(root, assets=True)
    except Exception as error:  # malformed or missing input must become report evidence
        return {
            "name": "contracts",
            "status": "FAIL",
            "errors": [f"contract validation failed: {error}"],
            "warnings": [],
        }
    return {
        "name": "contracts",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "project_id": data.get("production_brief", {}).get("project_id"),
    }


def _check_quality(root):
    path = root / "quality_report.json"
    if not path.is_file():
        return {"name": "quality_gate", "status": "FAIL", "errors": ["quality_report.json"]}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {"name": "quality_gate", "status": "FAIL", "errors": ["valid quality_report.json"]}
    status = data.get("status") if isinstance(data, dict) else None
    if status not in PASS_QUALITY_STATUSES:
        return {
            "name": "quality_gate",
            "status": "FAIL",
            "errors": [f"quality_report.json status must be PASS or PASS_WITH_NOTES (got {status!r})"],
            "reported_status": status,
        }
    return {
        "name": "quality_gate",
        "status": "PASS",
        "reported_status": status,
        "warnings": list(data.get("issues", [])) if status == "PASS_WITH_NOTES" else [],
    }


def _check_visual_review(root):
    path = root / "visual_review.json"
    if not path.is_file():
        return {"name": "visual_review", "status": "FAIL", "errors": ["visual_review.json"]}
    data = _read_visual_review(path)
    if data is None:
        return {"name": "visual_review", "status": "FAIL", "errors": ["valid visual_review.json"]}
    preview_reference = data.get("preview")
    preview = _resolve_preview_reference(root, preview_reference) if preview_reference else None
    issues = _visual_review_issues(root, path, preview_path=preview, data=data)
    if issues:
        return {
            "name": "visual_review",
            "status": "FAIL",
            "errors": issues,
            "review_status": data.get("review_status"),
        }
    return {
        "name": "visual_review",
        "status": "PASS",
        "review_status": data.get("review_status"),
        "preview": str(preview),
        "frames": len(data.get("frames", [])),
    }


def _check_revisions(root):
    entries, error = open_revision_entries(root)
    if error:
        return {"name": "revisions", "status": "FAIL", "errors": [error]}
    if entries:
        return {
            "name": "revisions",
            "status": "FAIL",
            "errors": [f"{item.get('id', '?')}: {item.get('feedback', 'open revision')}" for item in entries],
            "open": [item.get("id") for item in entries],
        }
    return {"name": "revisions", "status": "PASS", "open": []}


def _check_media(root, contract_check, visual_check):
    preview = visual_check.get("preview")
    if not preview:
        return {"name": "media", "status": "FAIL", "errors": ["approved visual review preview"]}
    path = Path(preview)
    if not path.is_file() or path.stat().st_size == 0:
        return {"name": "media", "status": "FAIL", "errors": [f"non-empty MP4: {path}"]}
    try:
        metadata = _probe_media(path)
    except (OSError, RuntimeError) as error:
        return {"name": "media", "status": "FAIL", "errors": [str(error)], "path": str(path)}

    brief = {}
    try:
        brief = json.loads((root / "production_brief.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    expected = (brief.get("format") or {}) if isinstance(brief, dict) else {}
    errors = []
    for key in ("width", "height"):
        if expected.get(key) is not None and metadata.get(key) != expected[key]:
            errors.append(f"MP4 {key}={metadata.get(key)}; expected {expected[key]}")
    expected_fps = _fps(expected.get("fps"))
    if expected_fps and metadata.get("fps") is not None and abs(metadata["fps"] - expected_fps) > 0.01:
        errors.append(f"MP4 fps={metadata['fps']}; expected {expected_fps}")
    duration_frames = expected.get("duration_frames")
    duration = metadata.get("duration_seconds")
    if duration_frames is not None and expected_fps and duration is not None:
        expected_duration = float(duration_frames) / expected_fps
        tolerance = max(0.08, 1.0 / expected_fps + 0.03)
        if abs(duration - expected_duration) > tolerance:
            errors.append(f"MP4 duration={duration:.3f}s; expected {expected_duration:.3f}s ± {tolerance:.3f}s")
    if errors:
        return {
            "name": "media",
            "status": "FAIL",
            "errors": errors,
            "path": str(path),
            "sha256": file_sha256(path),
            "metadata": metadata,
        }
    return {
        "name": "media",
        "status": "PASS",
        "path": str(path),
        "sha256": file_sha256(path),
        "metadata": metadata,
    }


def check(project, output=None):
    """Run and persist the delivery gate, returning its JSON report."""
    root = Path(project).resolve()
    report_path = Path(output).resolve() if output else root / "delivery_report.json"
    checks = []
    contracts = _check_contracts(root)
    checks.append(contracts)
    checks.append(_check_quality(root))
    visual = _check_visual_review(root)
    checks.append(visual)
    checks.append(_check_revisions(root))
    checks.append(_check_media(root, contracts, visual))
    blocking = [f"{item['name']}: {error}" for item in checks if item.get("status") == "FAIL" for error in item.get("errors", [])]
    report = {
        "version": "0.1",
        "project": str(root),
        "status": "PASS" if not blocking else "FAIL",
        "checks": checks,
        "blocking_issues": blocking,
        "source_fingerprint": source_fingerprint(root),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report"] = str(report_path)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the local dynamic-comic delivery gate")
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path, help="Where to write delivery_report.json")
    args = parser.parse_args(argv)
    report = check(args.project, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
