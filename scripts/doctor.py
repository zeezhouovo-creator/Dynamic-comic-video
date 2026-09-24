"""Check the local Dynamic Comic runtime without installing or uploading anything."""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MINIMUMS = {"python": (3, 10), "node": (18, 0), "npm": (8, 0)}


def parse_version(value):
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", str(value))
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())


def _check(name, ok, detail, fix=None):
    result = {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}
    if fix and not ok:
        result["fix"] = fix
    return result


def _command_version(command):
    candidates = [command]
    if os.name == "nt":
        candidates.extend([f"{command}.cmd", f"{command}.exe"])
    executable = next((shutil.which(candidate) for candidate in candidates if shutil.which(candidate)), None)
    if not executable:
        return None, f"{command} not found"
    try:
        completed = subprocess.run([executable, "--version"], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        return None, f"{command} failed: {error}"
    version = parse_version(completed.stdout or completed.stderr)
    return version, (completed.stdout or completed.stderr).strip()


def _version_ok(version, minimum):
    return version is not None and version[:2] >= minimum


def _renderer_check(renderer):
    renderer = Path(renderer).resolve()
    package = renderer / "package.json"
    if not package.is_file():
        return _check("renderer.package", False, str(package), "Run setup.ps1 or point --renderer to a Remotion project")
    try:
        manifest = json.loads(package.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return _check("renderer.package", False, "package.json is not valid JSON")
    if not isinstance(manifest, dict):
        return _check("renderer.package", False, "package.json must contain an object")
    has_remotion = any("remotion" in key for key in {**manifest.get("dependencies", {}), **manifest.get("devDependencies", {})})
    if not has_remotion:
        return _check("renderer.remotion", False, "package.json has no Remotion dependency")
    modules = renderer / "node_modules"
    if not modules.is_dir():
        return _check("renderer.node_modules", False, str(modules), "Run npm ci in the external renderer directory")
    return _check("renderer", True, str(renderer))


def diagnose(project=None, renderer=None):
    """Return deterministic local checks suitable for CLI or automation."""
    checks = []
    python_version = tuple(sys.version_info[:3])
    checks.append(_check("python", _version_ok(python_version, MINIMUMS["python"]), ".".join(map(str, python_version)), "Use Python 3.10 or newer"))
    for command in ("node", "npm"):
        version, detail = _command_version(command)
        checks.append(_check(command, _version_ok(version, MINIMUMS[command]), detail, f"Install {command} {MINIMUMS[command][0]} or newer"))
    for module in ("jsonschema", "PIL"):
        present = importlib.util.find_spec(module) is not None
        checks.append(_check(f"python.{module}", present, "available" if present else "not importable", "Run pip install -r requirements.txt"))
    checks.append(_renderer_check(renderer or ROOT / "assets" / "remotion"))
    if project:
        project = Path(project).resolve()
        checks.append(_check("project.directory", project.is_dir(), str(project), "Create the production project directory"))
        if project.is_dir():
            required = ["production_brief.json", "characters.json", "storyboard.json", "motion_plan.json"]
            missing = [name for name in required if not (project / name).is_file()]
            checks.append(_check("project.contracts", not missing, "ready" if not missing else "missing: " + ", ".join(missing), "Complete the four production contract files"))
    failed = [item for item in checks if item["status"] == "FAIL"]
    return {"status": "FAIL" if failed else "PASS", "checks": checks, "failed": len(failed)}


def main():
    parser = argparse.ArgumentParser(description="Check the local Dynamic Comic runtime")
    parser.add_argument("project", nargs="?", type=Path, help="Optional production project to inspect")
    parser.add_argument("--renderer", type=Path, help="External Remotion renderer directory")
    args = parser.parse_args()
    result = diagnose(args.project, args.renderer)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
