"""Run the local validation, quality gate, prepare and Remotion preview steps.

This is intentionally a thin orchestration layer.  It does not generate images,
upload files or change the user's story; it only prepares an external renderer
directory and copies its MP4 back to the production project.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from project_state import file_sha256, source_fingerprint


ROOT = Path(__file__).resolve().parents[1]


def npm_command():
    """Return the platform-specific npm executable name."""
    return "npm.cmd" if os.name == "nt" else "npm"


def _safe_name(value):
    """Keep shot ids from becoming paths when used in review filenames."""
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in value)


def review_points(project, shot=None):
    """Return first/middle/last local frames for each selected shot."""
    motion_path = Path(project) / "motion_plan.json"
    if not motion_path.is_file():
        return []
    data = json.loads(motion_path.read_text(encoding="utf-8"))
    shots = data.get("shots", [])
    if shot:
        shots = [item for item in shots if item.get("shot_id") == shot]
        if not shots:
            raise ValueError(f"Unknown shot: {shot}")
    points = []
    for item in shots:
        shot_id = item["shot_id"]
        duration = item["duration_frames"]
        local_frames = (0, max(0, (duration - 1) // 2), duration - 1)
        for position, frame in zip(("first", "middle", "last"), local_frames):
            points.append({
                "shot_id": shot_id,
                "position": position,
                "frame": frame,
                "global_frame": frame if shot else item["start_frame"] + frame,
                "filename": f"{_safe_name(shot_id)}_{position}.png",
            })
    return points


def steps(project, renderer, install=False, shot=None, stills=None):
    """Return the ordered commands used by :func:`run_preview`.

    Keeping command construction separate makes the one-click workflow easy to
    test without starting a renderer or touching a real production project.
    """
    python = sys.executable
    pipeline = ROOT / "scripts" / "pipeline.py"
    quality = ROOT / "scripts" / "quality_gate.py"
    validate_command = [python, str(pipeline), "validate", str(project), "--assets"]
    compile_command = [python, str(pipeline), "compile", str(project)]
    prepare_command = [python, str(pipeline), "prepare", str(project), "--renderer", str(renderer)]
    if shot:
        compile_command.extend(["--shot", shot])
        prepare_command.extend(["--shot", shot])
    result = [
        (validate_command, project),
        ([python, str(quality), str(project), "--autofix"], project),
        (list(validate_command), project),
        (compile_command, project),
        (prepare_command, project),
    ]
    if install:
        result.append(([npm_command(), "ci"], renderer))
    result.append(([npm_command(), "run", "render"], renderer))
    for point in stills or []:
        output = f"out/visual-review/{point['filename']}"
        result.append(([
            npm_command(), "run", "still-frame", "--", output,
            f"--frame={point['global_frame']}",
        ], renderer))
    return result


def run_preview(project, renderer, output=None, install=False, shot=None):
    """Build a full or shot preview MP4 and visual review frame manifest."""
    project = Path(project).resolve()
    renderer = Path(renderer).resolve()
    if not (project / "production_brief.json").is_file():
        raise FileNotFoundError(f"Not a production project: {project}")
    if renderer == project or renderer.is_relative_to(project):
        raise ValueError("Renderer must be outside the production project")
    renderer.mkdir(parents=True, exist_ok=True)
    points = review_points(project, shot)
    if points:
        (renderer / "out" / "visual-review").mkdir(parents=True, exist_ok=True)
    for command, cwd in steps(project, renderer, install, shot, points):
        print("RUN:", " ".join(str(part) for part in command))
        subprocess.run(command, cwd=str(cwd), check=True)

    rendered = renderer / "out" / "video.mp4"
    if not rendered.is_file():
        raise FileNotFoundError(f"Remotion did not produce {rendered}")
    destination = (Path(output).resolve() if output else project / (f"preview_{_safe_name(shot)}.mp4" if shot else "preview.mp4"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(rendered, destination)
    if points:
        review_root = project / "visual-review"
        review_root.mkdir(parents=True, exist_ok=True)
        frames = []
        for point in points:
            source = renderer / "out" / "visual-review" / point["filename"]
            if not source.is_file():
                raise FileNotFoundError(f"Remotion did not produce {source}")
            relative = Path("visual-review") / point["filename"]
            shutil.copy2(source, project / relative)
            frames.append({
                "shot_id": point["shot_id"],
                "position": point["position"],
                "frame": point["frame"],
                "global_frame": point["global_frame"],
                "image": relative.as_posix(),
                "sha256": file_sha256(project / relative),
                "reviewed": False,
            })
        try:
            preview_reference = destination.relative_to(project).as_posix()
        except ValueError:
            preview_reference = str(destination)
        (project / "visual_review.json").write_text(json.dumps({
            "version": "0.2",
            "preview": preview_reference,
            "preview_sha256": file_sha256(destination),
            "source_fingerprint": source_fingerprint(project),
            "scope": {"shot": shot, "full_project": shot is None},
            "frames": frames,
            "review_status": "pending",
            "review_notes": "Inspect identity, seams, contact, occlusion, captions and timing before marking reviewed.",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def main():
    parser = argparse.ArgumentParser(description="Build a local Dynamic Comic MP4 preview")
    parser.add_argument("project", type=Path, help="Independent production project directory")
    parser.add_argument("--renderer", type=Path, required=True, help="External Remotion renderer directory")
    parser.add_argument("--output", type=Path, help="Destination MP4; defaults to <project>/preview.mp4")
    parser.add_argument("--npm-install", action="store_true", help="Run npm ci before rendering")
    parser.add_argument("--shot", help="Render one shot and rebase its timeline to frame zero")
    args = parser.parse_args()
    destination = run_preview(args.project, args.renderer, args.output, args.npm_install, args.shot)
    visual_review = args.project.resolve() / "visual_review.json"
    if not visual_review.is_file():
        visual_review = None
    print(json.dumps({"status": "PASS", "preview": str(destination), "visual_review": str(visual_review) if visual_review else None}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
