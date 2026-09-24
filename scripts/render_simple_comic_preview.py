"""Render a short simple-comic preview from existing master shots.

The renderer keeps the approved master as the visual source of truth, but it
also accepts small, aligned face variants for speech and blinking.  The old
preview used those variants; the first simple-comic preview accidentally
reduced every shot to one repeated still.  ``simple_comic_motion.json`` makes
the local acting explicit again without adding camera motion or regenerating
the approved artwork.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np


FPS = 24


def _safe_path(path: Path) -> str:
    """Return a path suitable for FFmpeg's subtitles filter on Windows."""
    return str(path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def _ass_time(frame: int) -> str:
    total_ms = round(frame * 1000 / FPS)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{millis // 10:02d}"


def _stylize(source: Path, destination: Path) -> None:
    image = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Unable to read master image: {source}")

    # Keep the original composition and characters, while moving the finish
    # toward a clean flat-color comic: denoise gradients, quantize colors, and
    # draw a restrained dark ink contour.
    smooth = cv2.bilateralFilter(image, 9, 75, 75)
    hsv = cv2.cvtColor(smooth, cv2.COLOR_BGR2HSV)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.float32) * 1.08, 0, 255).astype(np.uint8)
    flat = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    levels = 28
    flat = np.clip((flat // levels) * levels + levels // 2, 0, 255).astype(np.uint8)

    gray = cv2.cvtColor(smooth, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 70, 155)
    edges = cv2.dilate(edges, np.ones((2, 2), np.uint8), iterations=1)
    flat[edges > 0] = (22, 22, 22)

    destination.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(destination), flat):
        raise OSError(f"Unable to write stylized image: {destination}")


def _build_ass(storyboard: dict, motion_plan: dict, destination: Path, width: int = 1080, height: int = 1440) -> None:
    font_size = max(36, round(height * 0.0375))
    margin_v = max(90, round(height * 0.11))
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,Microsoft YaHei,{font_size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H78000000,1,0,0,0,100,100,0,0,1,4,0,2,80,80,{margin_v},134",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    starts = {shot["shot_id"]: shot["start_frame"] for shot in motion_plan["shots"]}
    for shot in storyboard["shots"]:
        shot_start = starts[shot["id"]]
        for cue in shot.get("dialogue", []):
            text = str(cue.get("text", "")).replace("{", r"\{").replace("}", r"\}")
            if not text:
                continue
            start = shot_start + int(cue["start_frame"])
            end = shot_start + int(cue["end_frame"])
            lines.append(
                f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,160,,{text}"
            )
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_motion(project: Path, path: Path | None) -> dict:
    """Load optional local face-motion metadata without making it mandatory."""
    motion_path = path or project / "simple_comic_motion.json"
    if not motion_path.is_file():
        return {}
    data = json.loads(motion_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("simple_comic_motion.json must contain an object")
    shots = data.get("shots", [])
    if not isinstance(shots, list):
        raise ValueError("simple_comic_motion.json shots must be an array")
    return {item["shot_id"]: item for item in shots if isinstance(item, dict) and item.get("shot_id")}


def _resolve_variant(project: Path, value: str | None) -> Path | None:
    if not value:
        return None
    candidate = project / value
    return candidate if candidate.is_file() else None


def render(project: Path, output: Path, motion_config: Path | None = None) -> Path:
    storyboard_path = project / "storyboard.json"
    motion_path = project / "motion_plan.json"
    if not storyboard_path.is_file() or not motion_path.is_file():
        raise FileNotFoundError("Project must contain storyboard.json and motion_plan.json")
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    motion_plan = json.loads(motion_path.read_text(encoding="utf-8"))
    brief_path = project / "production_brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8")) if brief_path.is_file() else {}
    fmt = brief.get("format", {}) if isinstance(brief, dict) else {}
    width = int(fmt.get("width", 1080))
    height = int(fmt.get("height", 1440))
    motion = _load_motion(project, motion_config)
    shots = motion_plan.get("shots", [])
    if not shots:
        raise ValueError("motion_plan.json has no shots")
    first_dir = project / "shots" / shots[0]["shot_id"]
    first_master = first_dir / "master_simple_comic_v1.png"
    if not first_master.is_file():
        first_master = first_dir / "master.png"
    first_image = cv2.imread(str(first_master), cv2.IMREAD_COLOR)
    if first_image is not None:
        height, width = first_image.shape[:2]
    total_frames = sum(int(shot["duration_frames"]) for shot in shots)

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="simple-comic-preview-") as temp_dir:
        work = Path(temp_dir)
        frame_dir = work / "frames"
        frame_dir.mkdir(parents=True, exist_ok=True)
        ass = work / "subtitles.ass"
        frame_index = 0
        for shot in shots:
            shot_id = shot["shot_id"]
            shot_dir = project / "shots" / shot_id
            approved_master = shot_dir / "master_simple_comic_v1.png"
            master = approved_master if approved_master.is_file() else shot_dir / "master.png"
            if not master.is_file():
                raise FileNotFoundError(f"Missing master image: {master}")
            styled = work / f"{shot_id}.png"
            # Approved generated masters are already in the requested style;
            # keep them pixel-identical and only apply subtitles at encode time.
            if master.name == "master_simple_comic_v1.png":
                shutil.copy2(master, styled)
            else:
                _stylize(master, styled)
            spec = motion.get(shot_id, {})
            variants = spec.get("variants", {}) if isinstance(spec, dict) else {}
            variant_paths = {
                name: _resolve_variant(project, value)
                for name, value in variants.items()
                if isinstance(name, str) and isinstance(value, str)
            }
            mouth_frames = {int(frame) for frame in spec.get("mouth_open_frames", [])}
            blink_frames = {int(frame) for frame in spec.get("blink_frames", [])}
            for local_frame in range(int(shot["duration_frames"])):
                if local_frame in mouth_frames and local_frame in blink_frames:
                    frame_source = variant_paths.get("mouth_open_blink") or variant_paths.get("mouth_open")
                elif local_frame in mouth_frames:
                    frame_source = variant_paths.get("mouth_open")
                elif local_frame in blink_frames:
                    frame_source = variant_paths.get("blink")
                else:
                    frame_source = None
                # A CFR image sequence gives the subtitle filter exact frame
                # timestamps and avoids concat-demuxer duration rounding.
                frame_path = frame_dir / f"frame_{frame_index:04d}.png"
                shutil.copy2(frame_source or styled, frame_path)
                frame_index += 1
        _build_ass(storyboard, motion_plan, ass, width, height)

        command = [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(frame_dir / "frame_%04d.png"),
            "-vf",
            f"subtitles='{_safe_path(ass)}'",
            "-fps_mode",
            "cfr",
            "-r",
            str(FPS),
            "-frames:v",
            str(total_frames),
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ]
        subprocess.run(command, check=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a simple-comic MP4 preview from master shots")
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--motion-config", type=Path, help="Optional face-acting manifest; defaults to simple_comic_motion.json")
    args = parser.parse_args()
    output = args.output or args.project / "preview-simple-comic-10s.mp4"
    result = render(args.project.resolve(), output, args.motion_config.resolve() if args.motion_config else None)
    print(json.dumps({"status": "PASS", "preview": str(result)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
