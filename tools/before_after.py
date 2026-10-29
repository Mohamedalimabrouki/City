"""One labelled picture: a git ref ("before") above the working tree ("after"), same camera.

    python tools/before_after.py --view street [--ref HEAD] [--out output/checks/NAME.png]
    python tools/before_after.py --interior pick:dar [--city NAME] [--view interior|overview]

Both sides run `citygen build --quick`, then tools/snapshot.py. With --interior, each side then runs
`citygen interior SPEC --folder <its build>` and pictures that interior folder (a side without the
command shows a grey half, "Before: no interior yet"). Prints the mean absolute pixel difference
between the halves (0.0 = identical). Snapshots start a local web server: run outside the Claude
sandbox, or set sandbox.network.allowLocalBinding.
"""
from __future__ import annotations

import argparse
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ROOT / "output" / "checks"
COLUMNS, SPACING = 8, 4.0   # kit-sheet grid, see citygen/kitsheet.py
BINDING_HINT = "run outside the sandbox, or set sandbox.network.allowLocalBinding"


class ToolError(RuntimeError):
    """A step failed; the message says what to do."""


def _run(cmd: list[str], cwd: Path) -> str:
    done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if done.returncode != 0:
        tail = "\n".join((done.stdout + done.stderr).strip().splitlines()[-6:])
        if "Operation not permitted" in tail or "PermissionError" in tail:
            tail += f"\n{BINDING_HINT}"
        raise ToolError(f"{' '.join(cmd[:4])} failed in {cwd}:\n{tail}")
    return done.stdout


def _export_ref(ref: str, dest: Path) -> str:
    """Unpack the tree of `ref` into dest; returns the short hash."""
    short = subprocess.run(["git", "rev-parse", "--short", ref], cwd=ROOT, capture_output=True, text=True)
    if short.returncode != 0:
        raise ToolError(f"unknown git ref {ref!r}")
    tar = subprocess.run(["git", "archive", ref], cwd=ROOT, capture_output=True, check=True).stdout
    dest.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(tar)) as tf:
        members = [m for m in tf.getmembers() if not m.name.startswith((".claude", "docs", ".git"))]
        tf.extractall(dest, members=members, filter="data")
    # both halves must be seen through the same viewer, or a viewer change would show as a picture change
    shutil.copy2(ROOT / "tools" / "viewer" / "index.html", dest / "tools" / "viewer" / "index.html")
    return short.stdout.strip()


def _build(tree: Path, build_args: str) -> Path:
    """Quick build in `tree`; returns the folder the build reports ("done ... -> FOLDER")."""
    cmd = [sys.executable, "-m", "citygen", "build", "--quick", *shlex.split(build_args)]
    text = _run(cmd, tree)
    found = re.findall(r"done in .*? -> (.+)", text)
    if not found:
        raise ToolError(f"build in {tree} did not report an output folder")
    folder = Path(found[-1].strip())
    return folder if folder.is_absolute() else tree / folder


def _interior(tree: Path, build: Path, spec: str, city: str | None, required: bool) -> Path | None:
    """`citygen interior SPEC` on the build in `tree`; returns the folder it reports ("... -> FOLDER").
    A tree without the command (or that cannot make it) gives None, unless `required`."""
    cmd = [sys.executable, "-m", "citygen", "interior", spec, "--folder", str(build), *(["--city", city] if city else [])]
    done = subprocess.run(cmd, cwd=tree, capture_output=True, text=True)
    found = re.findall(r"^interior .*? -> (.+)$", done.stdout, re.MULTILINE)
    if done.returncode != 0 or not found:
        if required:
            tail = "\n".join((done.stdout + done.stderr).strip().splitlines()[-4:])
            raise ToolError(f"citygen interior {spec} failed in {tree}:\n{tail}")
        return None
    folder = Path(found[-1].strip())
    return folder if folder.is_absolute() else tree / folder


def _grey(png: Path, size: tuple[int, int]) -> None:
    from PIL import Image

    Image.new("RGB", size, (128, 128, 128)).save(png)


def _kit_sheet(tree: Path) -> Path:
    out = tree / "output" / "kit-sheet"
    _run([sys.executable, "-m", "citygen", "kit-sheet", "--out", str(out)], tree)
    return out


def _frame_camera(sheet: Path, piece: str) -> str:
    """Viewer query that looks at one kit-sheet piece (pieces face north, so stand north of it)."""
    for line in (sheet / "pieces.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) > 1 and parts[1] == piece:
            k = int(parts[0])
            break
    else:
        raise ToolError(f"piece {piece!r} not in {sheet / 'pieces.txt'}")
    rows = (sum(1 for _ in (sheet / "pieces.txt").open()) + COLUMNS - 1) // COLUMNS
    depth = rows * SPACING
    x, y = (k % COLUMNS + 0.5) * SPACING, depth - (k // COLUMNS + 0.5) * SPACING
    return f"cam={x:.2f},{y + 9:.2f},4.0&look={x:.2f},{y:.2f},1.0"


def _snapshot(tree: Path, folder: Path, png: Path, view: str, query: str, size: tuple[int, int],
              timeout: float) -> None:
    cmd = [sys.executable, str(tree / "tools" / "snapshot.py"), str(folder), "--png", str(png),
           "--view", view, "--width", str(size[0]), "--height", str(size[1]), "--timeout", str(timeout)]
    if query:
        cmd += ["--query", query]
    _run(cmd, tree)


def _label(image, text: str):
    from PIL import ImageDraw, ImageFont

    font = None
    for name in ("Arial.ttf", "DejaVuSans.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        try:
            font = ImageFont.truetype(name, 36)
            break
        except OSError:
            continue
    font = font or ImageFont.load_default(size=36)
    draw = ImageDraw.Draw(image)
    box = draw.textbbox((16, 12), text, font=font)
    draw.rectangle((box[0] - 8, box[1] - 6, box[2] + 8, box[3] + 6), fill=(0, 0, 0))
    draw.text((16, 12), text, fill=(255, 255, 255), font=font)


def _combine(before: Path, after: Path, before_label: str, out: Path) -> float:
    from PIL import Image, ImageChops, ImageStat

    a, b = Image.open(before).convert("RGB"), Image.open(after).convert("RGB")
    diff = ImageStat.Stat(ImageChops.difference(a, b)).mean
    _label(a, before_label)
    _label(b, "After (working tree)")
    sheet = Image.new("RGB", (a.width, a.height + b.height))
    sheet.paste(a, (0, 0))
    sheet.paste(b, (0, a.height))
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() in (".jpg", ".jpeg"):
        sheet.save(out, quality=85, optimize=True)
    else:
        sheet.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(out, optimize=True)
    return sum(diff) / len(diff)


def _has_view(folder: Path, view: str) -> bool:
    import json

    if view in ("aerial", "street", "top"):
        return True
    index = json.loads((folder / "tiles" / "index.json").read_text(encoding="utf-8"))
    return view in (index.get("views") or {})


def run(args) -> float:
    try:
        import PIL  # noqa: F401
    except ImportError as exc:
        raise ToolError("Pillow is not installed: pip install pillow") from exc
    width, height = (int(v) for v in args.size.lower().split("x"))
    half = (width, height)
    CHECKS.mkdir(parents=True, exist_ok=True)
    work = CHECKS / "_tmp_before"
    shutil.rmtree(work, ignore_errors=True)
    args.view = args.view or ("sheet" if args.kit_sheet else "interior" if args.interior else "aerial")
    out = Path(args.out) if args.out else CHECKS / f"before-after-{args.view}.png"
    try:
        short = _export_ref(args.ref, work / "before")
        if args.kit_sheet:
            b_dir, a_dir = _kit_sheet(work / "before"), _kit_sheet(ROOT)
        else:
            b_dir = _build(work / "before", args.build_args)
            a_dir = a_dir_for(args)
            if args.interior:
                b_dir = _interior(work / "before", b_dir, args.interior, args.city, required=False)
                a_dir = _interior(ROOT, a_dir, args.interior, args.city, required=True)
        parts = list(args.query)
        if args.cam and args.look:
            parts += [f"cam={args.cam}", f"look={args.look}"]
        if args.frame:
            parts.append(_frame_camera(a_dir, args.frame))
        query = "&".join(parts)
        before_view, note = args.view, ""
        if b_dir is not None and not _has_view(b_dir, args.view):
            before_view, note = "aerial", f" - no {args.view} view yet, aerial shown"
        shots = work / "shots"
        shots.mkdir()
        label = f"Before ({args.ref} {short}){note}"
        if b_dir is None:                      # --interior: the ref has no interior command yet
            _grey(shots / "b.png", half)
            label = "Before: no interior yet"
        else:
            _snapshot(work / "before", b_dir, shots / "b.png", before_view, query, half, args.timeout)
        _snapshot(ROOT, a_dir, shots / "a.png", args.view, query, half, args.timeout)
        diff = _combine(shots / "b.png", shots / "a.png", label, out)
    finally:
        if not args.keep:
            shutil.rmtree(work, ignore_errors=True)
    print(f"{out.resolve()} ({out.stat().st_size // 1024} KB)")
    print(f"mean pixel difference: {diff:.2f}")
    return diff


def a_dir_for(args) -> Path:
    if args.no_build:
        latest = sorted((ROOT / "output").glob("*/tiles/index.json"), key=lambda p: p.stat().st_mtime)
        if not latest:
            raise ToolError("--no-build: no built world in output/")
        return latest[-1].parents[1]
    return _build(ROOT, args.build_args)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Before (git ref) and after (working tree) in one picture.")
    ap.add_argument("--view", default=None, help="aerial, street, souk, top or a named view (interior, overview "
                                                 "with --interior)")
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--out", default=None)
    ap.add_argument("--query", action="append", default=[], metavar="K=V", help="extra viewer parameter, repeatable")
    ap.add_argument("--cam", default=None, help="x,y,z in meters (needs --look)")
    ap.add_argument("--look", default=None, help="x,y,z in meters")
    ap.add_argument("--build-args", default="", help='extra "citygen build --quick" arguments, e.g. "--out output/full"')
    ap.add_argument("--no-build", action="store_true", help="reuse the latest build of the working tree")
    ap.add_argument("--kit-sheet", action="store_true", help="compare kit sheets instead of the city")
    ap.add_argument("--frame", default=None, metavar="PIECE", help="with --kit-sheet: camera on one piece")
    ap.add_argument("--interior", default=None, metavar="SPEC",
                    help="picture one dwelling's interior (a number or pick:LAYOUT[:FLOORS]) on both sides")
    ap.add_argument("--city", default=None, help="with --interior: a city of the build (default: its main city)")
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--keep", action="store_true", help="keep the temporary before tree")
    args = ap.parse_args(argv)
    if bool(args.cam) != bool(args.look):
        ap.error("--cam and --look go together")
    if args.frame and not args.kit_sheet:
        ap.error("--frame needs --kit-sheet")
    if args.interior and args.kit_sheet:
        ap.error("--interior and --kit-sheet do not go together")
    if args.city and not args.interior:
        ap.error("--city needs --interior")
    try:
        run(args)
    except ToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
