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


ROOT = Path(__file__).resolve().parents[1]


def npm_command():
    """Return the platform-specific npm executable name."""
    return "npm.cmd" if os.name == "nt" else "npm"


def steps(project, renderer, install=False):
    """Return the ordered commands used by :func:`run_preview`.

    Keeping command construction separate makes the one-click workflow easy to
    test without starting a renderer or touching a real production project.
    """
    python = sys.executable
    pipeline = ROOT / "scripts" / "pipeline.py"
    quality = ROOT / "scripts" / "quality_gate.py"
    result = [
        ([python, str(pipeline), "validate", str(project), "--assets"], project),
        ([python, str(quality), str(project), "--autofix"], project),
        ([python, str(pipeline), "validate", str(project), "--assets"], project),
        ([python, str(pipeline), "compile", str(project)], project),
        ([python, str(pipeline), "prepare", str(project), "--renderer", str(renderer)], project),
    ]
    if install:
        result.append(([npm_command(), "ci"], renderer))
    result.append(([npm_command(), "run", "render"], renderer))
    return result


def run_preview(project, renderer, output=None, install=False):
    """Build a preview MP4 and return its absolute path."""
    project = Path(project).resolve()
    renderer = Path(renderer).resolve()
    if not (project / "production_brief.json").is_file():
        raise FileNotFoundError(f"Not a production project: {project}")
    if renderer == project or renderer.is_relative_to(project):
        raise ValueError("Renderer must be outside the production project")
    renderer.mkdir(parents=True, exist_ok=True)
    for command, cwd in steps(project, renderer, install):
        print("RUN:", " ".join(str(part) for part in command))
        subprocess.run(command, cwd=str(cwd), check=True)

    rendered = renderer / "out" / "video.mp4"
    if not rendered.is_file():
        raise FileNotFoundError(f"Remotion did not produce {rendered}")
    destination = (Path(output).resolve() if output else project / "preview.mp4")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(rendered, destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description="Build a local Dynamic Comic MP4 preview")
    parser.add_argument("project", type=Path, help="Independent production project directory")
    parser.add_argument("--renderer", type=Path, required=True, help="External Remotion renderer directory")
    parser.add_argument("--output", type=Path, help="Destination MP4; defaults to <project>/preview.mp4")
    parser.add_argument("--npm-install", action="store_true", help="Run npm ci before rendering")
    args = parser.parse_args()
    destination = run_preview(args.project, args.renderer, args.output, args.npm_install)
    print(json.dumps({"status": "PASS", "preview": str(destination)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
