"""Command line: python -m citygen <command>. Run `python -m citygen --help` for the list."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config, load_style


def _world_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--world", help="world settings file, e.g. worlds/example.toml")
    p.add_argument("--seed", type=int, help="starting number: same seed = same world")
    p.add_argument("--size-km", type=float, help="country width in kilometers")
    p.add_argument("--quick", action="store_true", help="small, fast world for tests")


def _config(args) -> dict:
    over: dict = {"world": {}, "build": {}}
    if args.seed is not None:
        over["world"]["seed"] = args.seed
    if args.size_km is not None:
        over["world"]["size_km"] = args.size_km
    if getattr(args, "out", None):
        over["build"]["output"] = args.out
    if getattr(args, "workers", None) is not None:
        over["build"]["workers"] = args.workers
    return load_config(args.world, over, quick=args.quick)


def _latest(folder: str | None) -> Path:
    if folder:
        return Path(folder)
    found = sorted(Path("output").glob("*/summary.json"), key=lambda p: p.stat().st_mtime)
    if not found:
        sys.exit("No built world found in output/. Run: python -m citygen build")
    return found[-1].parent


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m citygen",
                                 description="Generate an invented country with cities, as maps, data and 3D tiles.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="generate a world and export maps, data and 3D tiles")
    _world_args(b)
    b.add_argument("--area", help='what to export in 3D: "capital-center" (default), "capital", '
                                  '"city:NAME", "city-center:NAME", "box:X0,Y0,X1,Y1" (km), "all", "none"')
    b.add_argument("--out", help="output folder (default: output)")
    b.add_argument("--workers", type=int, help="processes that build tiles: 0 = all cores but one, "
                                               "1 = one process (default: [build] workers)")
    b.add_argument("--force", action="store_true", help="rebuild everything, ignoring earlier plans and tiles")

    ls = sub.add_parser("list", help="list the settlements of a world (fast, writes nothing)")
    _world_args(ls)

    v = sub.add_parser("view", help="open the 3D viewer in your web browser")
    v.add_argument("folder", nargs="?", help="a built world folder (default: the latest build)")
    v.add_argument("--port", type=int, default=8765)

    sn = sub.add_parser("snapshot", help="save a PNG of the 3D view (needs: pip install playwright)")
    sn.add_argument("folder", nargs="?", help="a built world folder (default: the latest build)")
    sn.add_argument("--png", default=None, help="output image (default: <folder>/maps/snapshot-<view>.png)")
    sn.add_argument("--view", default="aerial", help="aerial, street, souk or top")
    sn.add_argument("--width", type=int, default=1600)
    sn.add_argument("--height", type=int, default=900)

    ks = sub.add_parser("kit-sheet", help="every 3D piece (doors, shops, goods...) in one viewable grid")
    ks.add_argument("--out", default="output/kit-sheet")
    ks.add_argument("--kits", nargs="+", default=None, metavar="KIT",
                    help="kit names or folders to show (default: [build] kits)")

    ts = sub.add_parser("texture-sheet", help="every generated texture tiled 2 x 2, tinted, with its name")
    ts.add_argument("--out", default="output/checks/texture-sheet.png")
    ts.add_argument("--seed", type=int, help="texture seed (default: the world seed)")

    st = sub.add_parser("stats", help="short summary of a built world (cheap for agents to read)")
    st.add_argument("folder", nargs="?", help="a built world folder (default: the latest build)")
    st.add_argument("--tiles", action="store_true", help="bytes of every 3D tile by category, heaviest first")
    st.add_argument("--tile", help="with --tiles: detail this tile (e.g. tile_13_23) instead of the heaviest")

    args = ap.parse_args(argv)
    if args.cmd == "build":
        from .build import build
        cfg = _config(args)
        build(cfg, area=args.area, log=lambda msg: print(msg, flush=True), force=args.force)
    elif args.cmd == "list":
        from .world import generate_world
        world = generate_world(_config(args))
        print(f"{world.name} - seed {world.seed} - {world.size / 1000:.0f} km")
        for s in world.settlements:
            print(f"{s.id:4d}  {s.kind:8s} {s.name:22s} {s.population:9,d} people  "
                  f"at ({s.x / 1000:6.1f}, {s.y / 1000:6.1f}) km{'  coast' if s.coastal else ''}")
    elif args.cmd == "view":
        from .view import serve
        serve(_latest(args.folder), port=args.port)
    elif args.cmd == "snapshot":
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
        from snapshot import snapshot
        folder = _latest(args.folder)
        png = args.png or folder / "maps" / f"snapshot-{args.view}.png"
        snapshot(folder, png, view=args.view, width=args.width, height=args.height)
    elif args.cmd == "kit-sheet":
        from .kitsheet import kit_sheet
        print(kit_sheet(args.out, kits=args.kits))
    elif args.cmd == "texture-sheet":
        from .texturesheet import texture_sheet
        cfg = load_config()
        style = load_style(cfg["world"]["style"])
        seed = cfg["world"]["seed"] if args.seed is None else args.seed
        print(texture_sheet(args.out, style, seed))
    elif args.cmd == "stats":
        folder = _latest(args.folder)
        if args.tiles or args.tile:
            from .tilestats import tiles_report
            print(tiles_report(folder, tile=args.tile))
            return
        summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
        print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
