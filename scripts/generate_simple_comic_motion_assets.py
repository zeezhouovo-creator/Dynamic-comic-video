"""Create small aligned eye-blink and mouth-open variants for simple-comic masters.

The operation is local and deterministic.  It only edits the supplied face
regions and writes variants next to each master; it does not upload artwork or
call a remote image service.  The regions are deliberately explicit so a
reviewer can correct them when a new character or shot is introduced.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def _box(value, width: int, height: int) -> tuple[int, int, int, int]:
    x, y, w, h = (float(part) for part in value)
    left = max(0, min(width - 1, round(x * width)))
    top = max(0, min(height - 1, round(y * height)))
    right = max(left + 2, min(width, round((x + w) * width)))
    bottom = max(top + 2, min(height, round((y + h) * height)))
    return left, top, right, bottom


def _skin_color(image: np.ndarray, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    """Estimate a face fill color from the lower half of an eye region."""
    left, top, right, bottom = box
    crop = image[top + (bottom - top) // 2:bottom, left:right]
    if crop.size == 0:
        return (190, 190, 190)
    pixels = crop.reshape(-1, 3)
    bright = pixels[pixels.mean(axis=1) > 90]
    sample = bright if len(bright) else pixels
    return tuple(int(value) for value in np.median(sample, axis=0))


def _blink(image: np.ndarray, faces: list[dict], width: int, height: int) -> np.ndarray:
    eyes = [region for face in faces for region in face.get("eyes", [])]
    result = image.copy()
    for region in eyes:
        left, top, right, bottom = _box(region, width, height)
        center = ((left + right) // 2, (top + bottom) // 2)
        axes = (max(3, (right - left) // 2), max(2, (bottom - top) // 2))
        cv2.ellipse(result, center, axes, 0, 0, 360, _skin_color(image, (left, top, right, bottom)), -1)
        cv2.ellipse(result, center, (axes[0], max(2, axes[1] // 4)), 0, 200, 340, (32, 28, 28), max(2, round(width / 420)))
    return result


def _mouth_open(image: np.ndarray, faces: list[dict], width: int, height: int) -> np.ndarray:
    mouths = [face.get("mouth") for face in faces if face.get("mouth")]
    result = image.copy()
    for region in mouths:
        left, top, right, bottom = _box(region, width, height)
        center = ((left + right) // 2, (top + bottom) // 2)
        axes = (max(3, round((right - left) * 0.28)), max(3, round((bottom - top) * 0.33)))
        cv2.ellipse(result, center, axes, 0, 0, 360, (42, 28, 34), -1)
        tongue_center = (center[0], center[1] + max(1, axes[1] // 3))
        cv2.ellipse(
            result,
            tongue_center,
            (max(2, axes[0] // 2), max(1, axes[1] // 4)),
            0,
            0,
            180,
            (112, 102, 196),
            -1,
        )
    return result


def generate(project: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("shots"), list):
        raise ValueError("motion config must contain a shots array")
    for spec in config["shots"]:
        shot_id = spec.get("shot_id")
        if not shot_id:
            raise ValueError("motion config shot is missing shot_id")
        master_path = project / spec.get("master", f"shots/{shot_id}/master_simple_comic_v1.png")
        image = cv2.imread(str(master_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(f"Unable to read master image: {master_path}")
        height, width = image.shape[:2]
        faces = list((spec.get("faces") or {}).values())
        if not faces:
            raise ValueError(f"No face regions for {shot_id}")
        output_dir = project / "shots" / shot_id / "motion"
        output_dir.mkdir(parents=True, exist_ok=True)
        variants = {
            "mouth_open": output_dir / "mouth_open.png",
            "blink": output_dir / "blink.png",
            "mouth_open_blink": output_dir / "mouth_open_blink.png",
        }
        mouth_faces = [face for face in faces if face.get("character_id") == spec.get("speaker")]
        if not mouth_faces:
            mouth_faces = faces
        mouth = _mouth_open(image, mouth_faces, width, height)
        blink_ids = set(spec.get("blink_characters", [spec.get("speaker")]))
        blink_faces = [face for face in faces if face.get("character_id") in blink_ids]
        blink = _blink(image, blink_faces, width, height)
        both = _blink(mouth, blink_faces, width, height)
        for key, value in variants.items():
            if not cv2.imwrite(str(value), {"mouth_open": mouth, "blink": blink, "mouth_open_blink": both}[key]):
                raise OSError(f"Unable to write {value}")
        spec["variants"] = {key: path.relative_to(project).as_posix() for key, path in variants.items()}
    config["version"] = str(config.get("version", "0.1"))
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate local eye and mouth motion variants")
    parser.add_argument("project", type=Path)
    parser.add_argument("--config", type=Path, help="Motion manifest; defaults to <project>/simple_comic_motion.json")
    args = parser.parse_args()
    project = args.project.resolve()
    config = (args.config or project / "simple_comic_motion.json").resolve()
    result = generate(project, config)
    print(json.dumps({"status": "PASS", "shots": len(result["shots"]), "config": str(config)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
