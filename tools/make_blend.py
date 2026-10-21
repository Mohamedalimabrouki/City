"""Save a build as a ready-to-open Blender file, so Ali can follow the progress in Blender.

    python tools/make_blend.py [FOLDER] [--blender PATH] [--timeout SECONDS]

FOLDER is a built world (default: the latest build in output/). The file is the golden-hour
scene of tools/blender_beauty.py (built with --setup-only, nothing rendered) with one camera per
view of the tile index (aerial, street, souk, and any view later prompts add), saved next to the
tiles as <focus city>.blend, for example output/bodjantouna-42/goumosbane.blend.

Blender crashes at start inside the Claude sandbox (it probes the Metal GPU): run this outside it.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from citygen.export.lore import slug  # noqa: E402

BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
SANDBOX_HINT = ("Blender stopped before saving. If it crashed at start, it is probably running inside "
                "the Claude sandbox, which hides the GPU from it: run this command outside the sandbox.")

# Runs inside Blender after blender_beauty.py has built the scene: one camera per extra view, then save.
SAVE = """
import bpy, sys
sys.path.insert(0, {tools!r})
import blender_beauty as bb
scene = bpy.context.scene
_, index = bb.load_index({folder!r})
first = scene.camera
first.name = "Camera " + {views!r}[0]
for view in {views!r}[1:]:
    bb.setup_camera(scene, index, view)
    scene.camera.name = "Camera " + view
scene.camera = first
bpy.ops.wm.save_as_mainfile(filepath={out!r}, compress=True)
print("make_blend: saved", {out!r}, flush=True)
"""


def latest_build() -> Path:
    found = sorted((ROOT / "output").glob("*/summary.json"), key=lambda p: p.stat().st_mtime)
    if not found:
        sys.exit("No built world found in output/. Run: python -m citygen build --quick")
    return found[-1].parent


def views_of(index: dict) -> list[str]:
    """Camera views, the active one first: street when the index has it, then aerial, then the rest."""
    named = sorted(index.get("views", {}))
    first = ["street"] if "street" in named else []
    return first + ["aerial"] + [v for v in named if v != "street"]


def blend_path(folder: Path, index: dict) -> Path:
    return folder / f"{slug(index.get('focus', {}).get('name') or 'city')}.blend"


def command(blender: str, folder: Path, views: list[str], out: Path) -> list[str]:
    expr = SAVE.format(tools=str(ROOT / "tools"), folder=str(folder), views=views, out=str(out))
    return [blender, "-b", "--factory-startup", "--python", str(ROOT / "tools" / "blender_beauty.py"),
            "--python-expr", expr, "--", str(folder), "--view", views[0],
            "--png", f"//renders/{out.stem}.png", "--setup-only"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", nargs="?", help="a built world folder (default: the latest build)")
    ap.add_argument("--blender", default=BLENDER, help="path to the Blender program")
    ap.add_argument("--timeout", type=int, default=900, help="seconds before giving up")
    args = ap.parse_args()
    folder = Path(args.folder).resolve() if args.folder else latest_build()
    index_file = folder / "tiles" / "index.json"
    if not index_file.is_file():
        sys.exit(f"No tiles in {folder}: build with 3D tiles first (python -m citygen build --quick).")
    index = json.loads(index_file.read_text(encoding="utf-8"))
    views, out = views_of(index), blend_path(folder, index)
    run = subprocess.run(command(args.blender, folder, views, out), capture_output=True, text=True,
                         timeout=args.timeout)
    if "make_blend: saved" not in run.stdout:
        print("\n".join((run.stdout + run.stderr).splitlines()[-15:]))
        sys.exit(SANDBOX_HINT)
    print(f"Blender file: {out} ({out.stat().st_size / 1e6:.1f} MB, cameras: {', '.join(views)})")


if __name__ == "__main__":
    main()
