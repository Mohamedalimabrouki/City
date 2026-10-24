"""One full build: world, then city plans, then maps, data files and 3D tiles in an output folder."""
from __future__ import annotations

import json
import math
import multiprocessing
import os
import pickle
import shutil
import tempfile
import time
from pathlib import Path

from shapely.geometry import Point, box

from .buildkey import build_key
from .city import plan_city
from .city.ground import Ground
from .city.landmarks import landmark_views
from .city.port import view as port_view
from .city.station import view as station_view
from .city.streets import view_spot
from .export.lore import gazetteer, plan_json, slug, write_json
from .export.maps import city_map, country_map
from .mesh.tile import TileContext, export_tile
from .mesh.textures import write_shared_textures
from .world import generate_world


def output_dir(cfg: dict, world) -> Path:
    return Path(cfg["build"]["output"]) / f"{slug(world.name)}-{world.seed}"


def select_area(world, area: str) -> tuple:
    """(region to export as tiles or None, settlement to focus on, settlements to plan)."""
    kind, _, arg = area.strip().partition(":")
    cfg = world.cfg["build"]
    focus = world.capital()
    if kind == "none":
        return None, focus, [focus]
    if kind == "all":
        region = box(0.0, 0.0, world.size, world.size)
    elif kind in ("capital", "city"):
        focus = world.capital() if kind == "capital" else world.find(arg)
        region = Point(focus.x, focus.y).buffer(focus.radius * 1.15)
    elif kind in ("capital-center", "city-center"):
        focus = world.capital() if kind == "capital-center" else world.find(arg)
        region = Point(focus.x, focus.y).buffer(float(cfg["center_radius"]))
    elif kind == "box":
        x0, y0, x1, y1 = (float(v) * 1000.0 for v in arg.split(","))
        region = box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        c = region.centroid
        focus = min(world.settlements, key=lambda s: math.hypot(s.x - c.x, s.y - c.y))
    else:
        raise ValueError(f"unknown area {area!r}; see [build] area in citygen/defaults.toml")
    needed = [s for s in world.settlements if region.distance(Point(s.x, s.y)) < s.radius * 1.35]
    return region, focus, needed


def camera_views(plan, ground, reach: float = 600.0, style: dict | None = None) -> dict:
    """Eye-level camera spots near the city center (generator coords): the boulevard, a souk, and one on each
    boulevard landmark the city has, "cathedral" and "theatre" (prompt 32, the style's `[landmarks] camera`),
    "station" on the avenue before the railway station (prompt 33) and "port" over the harbor (prompt 34)."""
    center = Point(plan.settlement.x, plan.settlement.y)
    views = {}
    for name, kinds in (("street", ("boulevard", "arterial", "street")), ("souk", ("souk",))):
        spot = view_spot(plan.streets, center, kinds, reach)
        if spot is None:
            continue
        a, b = spot
        ga, gb = float(ground.surface(a.x, a.y)), float(ground.surface(b.x, b.y))
        views[name] = {"cam": [round(a.x, 1), round(a.y, 1), round(ga + 1.7, 1)],
                       "look": [round(b.x, 1), round(b.y, 1), round(gb + 4.0, 1)]}
    camera = (style or {}).get("landmarks", {}).get("camera")
    for name, ((cx, cy, ch), (lx, ly, lh)) in (landmark_views(plan, camera) if camera else {}).items():
        views[name] = {"cam": [round(cx, 1), round(cy, 1), round(float(ground.surface(cx, cy)) + ch, 1)],
                       "look": [round(lx, 1), round(ly, 1), round(float(ground.surface(lx, ly)) + lh, 1)]}
    spot = station_view(plan, ground)
    if spot is not None:
        views["station"] = spot
    spot = port_view(plan, ground, (style or {}).get("port", {}))
    if spot is not None:
        views["port"] = spot
    return views


def tiles_for(region, tile: int, world_size: float) -> list:
    minx, miny, maxx, maxy = region.bounds
    last = int(math.ceil(world_size / tile)) - 1
    keys = []
    for i in range(max(0, int(minx // tile)), min(last, int(maxx // tile)) + 1):
        for j in range(max(0, int(miny // tile)), min(last, int(maxy // tile)) + 1):
            if region.intersects(box(i * tile, j * tile, (i + 1) * tile, (j + 1) * tile)):
                keys.append((i, j))
    return keys


_worker_tc: TileContext | None = None  # one per worker process, built once by _init_worker


def resolve_workers(cfg: dict) -> int:
    """Worker processes to use: [build] workers, where 0 means all cores but one."""
    n = int(cfg["build"].get("workers", 1))
    return n if n > 0 else max(1, (os.cpu_count() or 2) - 1)


def _init_worker(path: str) -> None:
    """Runs in each worker: wait for the parent's pickle of world and plans, then load it."""
    global _worker_tc
    while not os.path.exists(path):  # the workers start while the parent is still planning
        time.sleep(0.05)
    with open(path, "rb") as f:
        world, plans = pickle.load(f)
    _worker_tc = TileContext(world, plans)


def _export_in_worker(job: tuple) -> dict:
    i, j, folder, journal = job
    return export_and_record(_worker_tc, i, j, folder, journal)


def export_and_record(tc, i: int, j: int, folder: Path, journal: Path | None) -> dict:
    """Export one tile, then write down in `journal` that it is finished (a note per tile)."""
    entry = export_tile(tc, i, j, folder)
    if journal is not None:
        journal.mkdir(parents=True, exist_ok=True)
        note = journal / f"tile_{i}_{j}.json"
        part = note.with_suffix(".part")
        part.write_text(json.dumps(entry), encoding="utf-8")
        os.replace(part, note)
    return entry


class TilePool:
    """Worker processes that export tiles; with one worker it is today's sequential path.

    With more, the processes start at once, so their start-up overlaps the parent's planning.
    The parent pickles world and plans once into a temporary file; each worker builds its own
    TileContext from it, so tiles share nothing and the bytes are the same as with one process.
    """

    def __init__(self, workers: int):
        self.workers = workers
        self.pool = self.tmp = None
        if workers > 1:
            self.tmp = tempfile.TemporaryDirectory(prefix="citygen-")
            self.shared = Path(self.tmp.name) / "world.pkl"
            # multiprocessing.Pool, not ProcessPoolExecutor: the Claude sandbox forbids the
            # os.sysconf("SC_SEM_NSEMS_MAX") check that ProcessPoolExecutor runs when it starts
            self.pool = multiprocessing.get_context("spawn").Pool(
                workers, initializer=_init_worker, initargs=(str(self.shared),))

    def __enter__(self) -> "TilePool":
        return self

    def __exit__(self, *exc) -> None:
        if self.pool is not None:
            self.pool.terminate()
            self.tmp.cleanup()

    def export(self, world, plans: list, keys: list, folder: Path, progress, meanwhile=lambda: None,
               journal: Path | None = None) -> list:
        """Export every tile in `keys`; returns the tile entries in the same order.

        `meanwhile` is the parent's own work (writing data files and maps): it runs while the
        workers load the world. Each finished tile leaves a note in the `journal` folder, so an
        interrupted build knows what is done.
        """
        if not keys or self.pool is None:
            meanwhile()
            tiles = []
            tc = TileContext(world, plans) if keys else None   # nothing to export: skip the costly setup
            for n, (i, j) in enumerate(keys, 1):
                tiles.append(export_and_record(tc, i, j, folder, journal))
                progress(n)
            return tiles
        part = self.shared.with_suffix(".part")
        with open(part, "wb") as f:
            pickle.dump((world, plans), f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(part, self.shared)  # workers only see the finished file
        results = self.pool.imap_unordered(_export_in_worker, [(i, j, folder, journal) for i, j in keys])
        meanwhile()
        done = {}
        for n, entry in enumerate(results, 1):
            done[(entry["i"], entry["j"])] = entry
            progress(n)
        return [done[k] for k in keys]


def export_tiles(world, plans: list, keys: list, folder: Path, workers: int, progress,
                 meanwhile=lambda: None, journal: Path | None = None) -> list:
    with TilePool(workers) as pool:
        return pool.export(world, plans, keys, folder, progress, meanwhile, journal)


def tile_files(entry: dict) -> list:
    """Every file a tile entry lists (later steps add texture and lod files to the entry)."""
    return [entry["file"], *entry.get("files", [])]


def finished_tiles(folder: Path, journal: Path, key: str, keys: list) -> dict:
    """Entries of tiles already built with this key: from the last finished build's index.json
    and from the journal (a note per tile) of an interrupted one. A tile counts only if all its files exist."""
    found = {}
    index = folder / "index.json"
    if index.is_file():
        old = json.loads(index.read_text(encoding="utf-8"))
        if old.get("build_key") == key:
            found.update({(t["i"], t["j"]): t for t in old["tiles"]})
    for note in sorted(journal.glob("tile_*.json")) if journal.is_dir() else []:
        try:
            entry = json.loads(note.read_text(encoding="utf-8"))
        except ValueError:
            continue
        found[(entry["i"], entry["j"])] = entry
    return {k: found[k] for k in keys
            if k in found and all((folder / f).is_file() for f in tile_files(found[k]))
            and (folder / found[k]["file"]).stat().st_size == found[k]["bytes"]}


def load_or_plan(world, s, cache: Path, key12: str, force: bool, log):
    """The plan of settlement `s`: from the cache when the key matches, else planned and cached."""
    path = cache / f"{slug(s.name)}-{key12}.pkl"
    if not force and path.is_file():
        try:
            plan = pickle.loads(path.read_bytes())
        except Exception:   # a damaged cache file is only a cache miss
            plan = None
        if plan is not None:
            plan.settlement = s   # the pickle holds a copy; build.py compares settlements with `is`
            log(f"plan reused {s.name} ({s.kind}): {plan.stats['buildings']:,} buildings")
            return plan
    plan = plan_city(world, s)
    cache.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".part")
    part.write_bytes(pickle.dumps(plan, protocol=pickle.HIGHEST_PROTOCOL))
    os.replace(part, path)
    st = plan.stats
    log(f"planned {s.name} ({s.kind}): {st['buildings']:,} buildings, {st['streets']:,} streets "
        f"[{st['seconds']}s]")
    return plan


def data_files_current(out: Path, key: str, plans: list) -> bool:
    """True when the last finished build had this key and its maps and data files are all there."""
    try:
        old = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    names = [slug(p.settlement.name) for p in plans]
    files = [out / "world.json", out / "gazetteer.md", out / "maps" / "country.png"]
    files += [out / "cities" / n / "plan.json" for n in names] + [out / "maps" / f"{n}.png" for n in names]
    return old.get("build_key") == key and all(f.is_file() for f in files)


def clean_cache(cache: Path, key12: str, force: bool) -> None:
    """Delete cache files and folders of other builds (all of them with --force)."""
    if cache.is_dir():
        for path in cache.iterdir():
            if force or not path.name.endswith((f"-{key12}.pkl", f"-{key12}")):
                shutil.rmtree(path) if path.is_dir() else path.unlink()


def build(cfg: dict, area: str | None = None, log=print, force: bool = False) -> Path:
    t0 = time.perf_counter()
    area = area or cfg["build"]["area"]
    world = generate_world(cfg)
    out = output_dir(cfg, world)
    out.mkdir(parents=True, exist_ok=True)
    log(f"world {world.name} (seed {world.seed}): {len(world.settlements)} settlements, "
        f"{len(world.roads)} roads [{time.perf_counter() - t0:.1f}s]")

    region, focus, needed = select_area(world, area)
    size = int(cfg["tiles"]["size"])
    keys = []
    if region is not None:
        keys = tiles_for(region, size, world.size)
        keys.sort(key=lambda k: math.hypot((k[0] + 0.5) * size - focus.x, (k[1] + 0.5) * size - focus.y))
    key = build_key(cfg, [s.id for s in needed])
    cache = out / "cache"
    clean_cache(cache, key[:12], force)
    folder = out / "tiles"
    journal = cache / f"tiles-{key[:12]}"
    done = {}
    if keys:
        folder.mkdir(parents=True, exist_ok=True)
        for stale in folder.glob("*.part"):   # tiles an interrupted build left half written
            stale.unlink()
        texture_mode = str(cfg["tiles"].get("textures", "shared"))
        if texture_mode == "shared":   # once, here: parallel workers must never race on one image
            written = write_shared_textures(world.style, world.seed, folder)
            if written:
                log(f"textures: {len(written)} shared images in tiles/textures")
        if not force:
            done = finished_tiles(folder, journal, key, keys)
    todo = [k for k in keys if k not in done]
    workers = resolve_workers(cfg)
    if len(todo) <= 2 * workers:  # too few tiles to repay starting the processes
        workers = 1
    if done:
        log(f"tiles reused: {len(done)} of {len(keys)}")
    if workers > 1:
        log(f"exporting {len(todo)} tiles with {workers} workers")

    with TilePool(workers) as pool:  # its processes start now and wait while the parent plans
        plans = [load_or_plan(world, s, cache, key[:12], force, log) for s in needed]

        def write_files() -> None:  # the parent's own writing, done while workers start up
            if not force and data_files_current(out, key, plans):
                log("maps and data files reused")
                return
            (out / "summary.json").unlink(missing_ok=True)   # written again last: files cut short never count as current
            write_json(out / "world.json", world.to_json())
            country_map(world, out / "maps" / "country.png")
            for plan in plans:
                write_json(out / "cities" / slug(plan.settlement.name) / "plan.json", plan_json(plan))
                city_map(world, plan, out / "maps" / f"{slug(plan.settlement.name)}.png")
            (out / "gazetteer.md").write_text(gazetteer(world, plans), encoding="utf-8")

        tiles = []
        if region is None:
            write_files()
        else:
            step = max(1, len(todo) // 10)
            def progress(n: int) -> None:
                if n % step == 0 or n == len(todo):
                    log(f"tiles {n}/{len(todo)} [{time.perf_counter() - t0:.0f}s]")

            built = iter(pool.export(world, plans, todo, folder, progress, write_files, journal))
            tiles = [done[k] if k in done else next(built) for k in keys]
            ground = Ground(world, plans)
            write_json(folder / "index.json", {
                "format": "citygen-tiles/1", "build_key": key, "seed": world.seed, "world_name": world.name,
                "tile_size": size, "world_size": [world.size, world.size],
                "parapets": True,   # the tiles carry their own roof parapets (tools/blender_beauty.py skips its own)
                "focus": {"x": round(focus.x, 1), "y": round(focus.y, 1),
                          "z": round(float(ground.surface(focus.x, focus.y)), 1), "name": focus.name},
                "views": next((camera_views(p, ground, style=world.style) for p in plans if p.settlement is focus), {}),
                "cities": [{"name": p.settlement.name, "plan": f"cities/{slug(p.settlement.name)}/plan.json",
                            "bounds": [round(v, 1) for v in p.boundary.bounds]} for p in plans],
                "tiles": tiles})

        summary = {
            "world": world.name, "build_key": key, "seed": world.seed, "size_km": world.size / 1000.0, "area": area,
            "settlements": {k: sum(s.kind == k for s in world.settlements) for k in ("capital", "city", "town", "village")},
            "roads": len(world.roads),
            "plans": [{"name": p.settlement.name, "kind": p.settlement.kind, **p.stats} for p in plans],
            "tiles": {"count": len(tiles), "triangles": sum(t["triangles"] for t in tiles),
                      "drawn_triangles": sum(t.get("drawn", t["triangles"]) for t in tiles),
                      "dressing_pieces": sum(t.get("pieces", 0) for t in tiles),
                      "megabytes": round(sum(t["bytes"] for t in tiles) / 1e6, 1)},
            "seconds": round(time.perf_counter() - t0, 1),
        }
        write_json(out / "summary.json", summary)
        log(f"done in {summary['seconds']}s -> {out}")

    return out
