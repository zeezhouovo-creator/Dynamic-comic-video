"""Synthetic fixture for head, hand and prop acting with a fixed camera."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from make_acting_fixture import build as build_base
from pipeline import read, save


def keys(part):
    if part == "head":
        return [(0, 0, 0), (10, -3, 0), (22, -3, 0), (47, 0, 0)]
    if part == "hand":
        return [(0, 0, 0), (10, 8, -2), (22, 8, -2), (47, 0, 0)]
    return [(0, 0, 0), (10, 12, 0), (22, 12, 0), (47, 0, 0)]


def build(root):
    root = Path(root)
    build_base(root)
    board = read(root / "storyboard.json")
    motion = read(root / "motion_plan.json")
    for board_shot, motion_shot in zip(board["shots"], motion["shots"]):
        board_shot["dialogue"] = []
        motion_shot["performance"]["mode"] = "limited-animation"
        motion_shot["performance"]["intent"] = (
            "Fixed camera: one head turn, one hand gesture and one prop adjustment; "
            "each returns to a stable hold."
        )
        motion_shot["performance"]["static_reason"] = "Stable holds separate the three event-driven actions."
        folder = root / "shots" / board_shot["id"] / "layers"
        offset = int(board_shot["id"][-1]) - 1
        assets = {}
        head = Image.new("RGBA", (960, 540))
        draw = ImageDraw.Draw(head)
        draw.ellipse((350, 78, 460, 188), fill="#f2b074", outline="#172332", width=4)
        hand = Image.new("RGBA", (960, 540))
        draw = ImageDraw.Draw(hand)
        draw.ellipse((585, 245, 625, 285), fill="#edac58", outline="#172332", width=3)
        prop = Image.new("RGBA", (960, 540))
        draw = ImageDraw.Draw(prop)
        draw.rounded_rectangle((610, 180, 690, 250), 8, fill="#6c8fc4", outline="#172332", width=4)
        for name, image in (("head", head), ("hand", hand), ("prop", prop)):
            if offset:
                shifted = Image.new("RGBA", image.size)
                shifted.alpha_composite(image, (offset, offset))
                image = shifted
            path = folder / f"{name}.png"
            image.save(path)
            assets[name] = f"shots/{board_shot['id']}/layers/{name}.png"
            with Image.open(folder.parent / "master.png") as master:
                combined = master.convert("RGBA")
            combined.alpha_composite(image)
            combined.save(folder.parent / "master.png")

        for name, part, z, trigger, description in (
            ("head", "head", 15, "emotion", "A brief listening head turn, then settle."),
            ("hand", "hand", 25, "action", "A single small hand gesture, then return to rest."),
            ("prop", "prop", 35, "information", "The prop shifts once to reveal the action, then holds."),
        ):
            if not any(layer["id"] == name for layer in board_shot["layers"]):
                board_shot["layers"].append({
                    "id": name,
                    "role": "character",
                    "character_id": "lin",
                    "elements": f"Synthetic {name} acting layer",
                    "method": "extract",
                    "reason": "Validate one local event without moving the camera.",
                })
            plan_keys = [
                {"frame": frame, "x": x, "y": 0, "rotation": rotation, "opacity": 1}
                for frame, x, rotation in keys(part)
            ]
            if not any(layer["layer_id"] == name for layer in motion_shot["layers"]):
                motion_shot["layers"].append({
                    "layer_id": name,
                    "asset": assets[name],
                    "z": z,
                    "from": {"x": 0, "y": 0, "scale": 1},
                    "to": {"x": 0, "y": 0, "scale": 1},
                    "acting": {
                        "part": part,
                        "pivot": [0.5, 0.5],
                        "keys": plan_keys,
                        "events": [{
                            "event_id": f"{name}_event",
                            "trigger": trigger,
                            "start_frame": 6,
                            "peak_frame": 10,
                            "settle_frame": 22,
                            "end_frame": 28,
                            "description": description,
                        }],
                    },
                })
    save(root / "storyboard.json", board)
    save(root / "motion_plan.json", motion)
    return root


if __name__ == "__main__":
    target = Path(sys.argv[1])
    if target.exists():
        raise SystemExit("Use a new output directory")
    print(build(target))
