"""The interior folder (SPEC 6c "Output"): `tiles/interior.glb`, `tiles/index.json` and `rooms.json`.

A folder like a build, so `citygen view`, `citygen snapshot`, `tools/before_after.py` and the Blender
tools open it. Every file is written as `.part` and renamed; the index comes last.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

from shapely.ops import polylabel

from ..city.massing import main_mass
from ..mesh.builder import MeshBuilder, add_cap
from ..mesh.gltf import write_glb
from ..mesh.textures import encoded, image_names, spec_for
from ..mesh.props import tree_mesh
from ..mesh.tile import building_mesh, instance_groups

FLOOR = "paving"            # placeholder floor caps (prompt 49 lays real floors)
HOMES = ("house", "domed", "villa")   # "Dar <family>", as the viewer's card names them


def write_folder(interior, outside, out) -> Path:
    """Write the interior's folder at `out`; returns it."""
    out = Path(out)
    world, b = outside.ctx.world, outside.b
    cfg = world.style.get("interiors", {})
    margin = float(cfg.get("margin", 2.0))
    minx, miny, maxx, maxy = b.footprint.bounds
    x0, y0 = math.floor(minx - margin), math.floor(miny - margin)
    mb = MeshBuilder(origin=(x0, y0))
    building_mesh(mb, b, outside.ctx.ground.height, roofs=outside.roofs)   # the tile's shell (prompt 48 replaces it)
    for st in interior.storeys:
        add_cap(mb, st.polygon, st.z, FLOOR)
    instances = instance_groups(outside, outside.placements + court_trees(interior, outside, mb), x0, y0)
    parts = mb.gltf_parts()
    materials = {**outside.kit.materials, **cfg.get("palette", {})}
    images = used_images(world.style, world.seed, materials, [*parts, *(m for g in instances for m in g["parts"])])
    tiles = out / "tiles"
    tiles.mkdir(parents=True, exist_ok=True)
    glb = tiles / "interior.glb"
    part = glb.with_name(glb.name + ".part")
    size = write_glb(part, parts, materials, translation=(x0, 0.0, -y0), name="interior",
                     extras={"building": interior.building, "city": interior.city, "x0": x0, "y0": y0},
                     instances=instances, images=images)
    os.replace(part, glb)
    triangles = mb.triangles + sum(outside.kit.pieces[g["name"]].triangles for g in instances)
    _write_json(out / "rooms.json", interior.to_json())
    _write_json(tiles / "index.json", index_of(interior, outside, cfg, x0, y0, max(maxx - minx, maxy - miny),
                                               {"i": 0, "j": 0, "file": glb.name, "x0": x0, "y0": y0,
                                                "triangles": triangles, "bytes": size}))
    return out


def court_trees(interior, outside, mb) -> list:
    """The plan's trees standing in the court, as the tile draws them: kit pieces (`Dresser.tree`, on the
    tree's own stream) or, without a tree piece, the generator's mesh."""
    out = []
    dresser = outside.ctx.dresser(outside.plan)
    for f in interior.features:
        if f["type"] != "tree":
            continue
        t = outside.plan.trees[f["tree"]]
        z = float(outside.ctx.ground.surface(t.x, t.y))
        got = dresser.tree(f["tree"], t, z)
        if got is not None:
            out.append(got)
        else:
            tree_mesh(mb, t, z)
    return out


def used_images(style: dict, seed: int, materials: dict, names) -> dict:
    """Embedded images for the textures these materials use, and no other (`mesh/textures.encoded`)."""
    known = set(image_names(style))
    wanted = sorted({materials.get(m, {}).get("texture") for m in names} & known)
    out = {}
    for name in wanted:
        enc = encoded(name, seed, spec_for(style, name))
        out[name] = {"bytes": enc.data, "mime": enc.mime}
    return out


def index_of(interior, outside, cfg: dict, x0: int, y0: int, extent: float, entry: dict) -> dict:
    """`tiles/index.json`: one tile, a focus on the house, the `interior` and `overview` views."""
    b = outside.b
    c = b.footprint.centroid
    home = interior.household
    name = (f"No. {interior.building}" if home is None else
            f"Dar {home['family']}" if b.kind in HOMES else f"The {home['family']} family")
    return {"format": "citygen-tiles/1", "world_name": f"{interior.city} No. {interior.building} ({interior.layout})",
            "seed": interior.seed, "tile_size": int(math.ceil(extent + 4.0)), "parapets": True,
            "focus": {"x": round(c.x, 1), "y": round(c.y, 1), "z": round(interior.high, 1), "name": name},
            "views": {"interior": inside_view(interior, outside, cfg), "overview": overview(b, interior.high, extent)},
            "interior": {"building": interior.building, "city": interior.city, "layout": interior.layout,
                         "floors": [round(s.z, 3) for s in interior.storeys],
                         "roof": round(interior.high + main_mass(b).top, 3)},
            "cities": [], "tiles": [entry]}


def inside_view(interior, outside, cfg: dict) -> dict:
    """Eye height on the pole of inaccessibility of the main room, looking at its focus opening `look` m up:
    the layout's `focus` (dar: from the court to the T room's door; compact: from the covered court to the
    main bit's door; small: the bit toward its window), else floor 0 toward the main door."""
    if interior.focus is not None:
        room, op = interior.rooms[interior.focus[0]], interior.openings[interior.focus[1]]
        p = polylabel(room.polygon, tolerance=0.05)
        eye, look = float(cfg.get("eye", 1.6)), float(cfg.get("look", 1.4))
        return {"cam": [round(p.x, 3), round(p.y, 3), round(room.z + eye, 3)],
                "look": [round(op.x, 3), round(op.y, 3), round(room.z + look, 3)]}
    room = interior.rooms[0]
    p = polylabel(room.polygon, tolerance=0.05)
    doors = [o for o in interior.openings if o.floor == room.floor and o.kind in ("door", "shop")]
    main = outside.doors[0] if outside.doors else None
    if doors and main is not None:
        target = min(doors, key=lambda o: (math.hypot(o.x - main.x, o.y - main.y), o.id))
        tx, ty = target.x, target.y
    elif interior.openings:
        tx, ty = interior.openings[0].x, interior.openings[0].y
    else:
        tx, ty = room.polygon.centroid.x, room.polygon.centroid.y
    eye, look = float(cfg.get("eye", 1.6)), float(cfg.get("look", 1.4))
    return {"cam": [round(p.x, 3), round(p.y, 3), round(room.z + eye, 3)],
            "look": [round(tx, 3), round(ty, 3), round(room.z + look, 3)]}


def overview(b, high: float, extent: float) -> dict:
    """From the south-west, 45 degrees up, 1.5 x the footprint's larger side + the height from its center."""
    c = b.footprint.centroid
    z = high + b.height / 2
    d = 1.5 * extent + b.height
    return {"cam": [round(c.x - d / 2, 3), round(c.y - d / 2, 3), round(z + d * math.sqrt(0.5), 3)],
            "look": [round(c.x, 3), round(c.y, 3), round(z, 3)]}


def _write_json(path: Path, data: dict) -> None:
    part = path.with_name(path.name + ".part")
    part.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    os.replace(part, path)
