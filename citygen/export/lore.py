"""Data files for games and stories: world.json, cities/<name>/plan.json and gazetteer.md."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from ..city.geo import polygons


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "unnamed"


def _rings(poly) -> list:
    return [np.round(np.asarray(r.coords), 2).tolist() for r in [poly.exterior, *poly.interiors]]


def _geometry(geom) -> dict:
    ps = polygons(geom)
    if len(ps) == 1:
        return {"type": "Polygon", "coordinates": _rings(ps[0])}
    return {"type": "MultiPolygon", "coordinates": [_rings(p) for p in ps]}


def write_json(path, data) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    return path


def plan_json(plan) -> dict:
    """The full plan of one city. Geometry is GeoJSON-style, in world meters (x east, y north)."""
    return {
        "format": "citygen-city/1",
        "settlement": plan.settlement.to_json(),
        "stats": plan.stats,
        "boundary": _geometry(plan.boundary),
        "districts": [{"id": d.id, "kind": d.kind, "name": d.name, "geometry": _geometry(d.polygon)}
                      for d in plan.districts],
        "streets": [{"kind": s.kind, "width": s.width, "coords": np.round(np.asarray(s.line.coords), 2).tolist()}
                    for s in plan.streets],
        "buildings": [{"kind": b.kind, "district": b.district, "height": round(b.height, 2),
                       "floors": b.floors, "wall": b.wall, "roof": b.roof, "roof_shape": b.roof_shape,
                       "footprint": _rings(b.footprint),
                       **({"domes": [[round(x, 2), round(y, 2), round(r, 2), m] for x, y, r, m in b.domes]}
                          if b.domes else {}),
                       **_massing_json(b)}
                      for b in plan.buildings],
        "trees": [[round(t.x, 2), round(t.y, 2), t.kind, round(t.height, 1)] for t in plan.trees],
        "landmarks": [{"kind": m.kind, "name": m.name, "x": round(m.x, 1), "y": round(m.y, 1)}
                      for m in plan.landmarks],
        "households": [{"building": h.building, "family": h.family, "trade": h.trade, "wealth": h.wealth,
                        "door": h.door, "members": h.members} for h in plan.households],
        "souks": [{"street": k.street, "name": k.name, "trade": k.trade} for k in plan.souks],
        **_station_json(plan),
        **_port_json(plan),
    }


def _station_json(plan) -> dict:
    """The railway (prompt 33): each track's center line and the corridor kept clear, when the city has one."""
    st = getattr(plan, "station", None)
    if st is None:
        return {}
    return {"rail": {"tracks": [np.round(np.asarray(t.coords), 2).tolist() for t in st.tracks],
                     "corridor": _geometry(st.corridor)}}


def _port_json(plan) -> dict:
    """The harbor (prompt 34): quay edges, aprons, breakwater center lines, basins and lighthouses."""
    port = getattr(plan, "port", None)
    if port is None:
        return {}
    return {"port": {"level": port.level,
                     "quays": [{"district": q.district, "edge": np.round(np.asarray(q.line.coords), 2).tolist(),
                                "apron": _geometry(q.apron)} for q in port.quays],
                     "breakwaters": [{"line": np.round(np.asarray(bw.line.coords), 2).tolist(), "quay": bw.quay,
                                      "basin": _geometry(bw.basin),
                                      "lighthouse": {"x": round(bw.light[0], 2), "y": round(bw.light[1], 2),
                                                     "scheme": bw.light[3]}} for bw in port.breakwaters]}}


def _massing_json(b) -> dict:
    """The massing fields of a building (prompt 23), only those it uses."""
    out = {}
    if b.setback is not None:
        out["setback"] = _rings(b.setback)
    if b.steps:
        out["steps"] = [{"footprint": _rings(p), "floors": f, "roof_shape": shape, "roof": roof}
                        for p, f, shape, roof in b.steps]
    if b.top and "x" in b.top:
        out["top"] = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in b.top.items()}
    if b.machines:
        out["machines"] = [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in m.items()} for m in b.machines]
    if b.menzah:
        out["menzah"] = True
    if b.corners:
        out["corners"] = [[round(x, 2), round(y, 2), kind] for x, y, kind, _reach in b.corners]
    if b.apron is not None:
        out["apron"] = [_rings(p) for p in polygons(b.apron)]
    return out


def gazetteer(world, plans) -> str:
    """A readable guide to the world, for writing stories."""
    km = world.size / 1000.0
    lines = [f"# {world.name}", "",
             f"A generated country, {km:.0f} by {km:.0f} km, seed {world.seed}, style "
             f"\"{world.style.get('name', world.cfg['world']['style'])}\". "
             f"Rebuilding with the same seed and settings gives exactly this world again.", ""]
    cap = world.capital()
    lines += ["## The capital", "", _describe(cap), ""]
    for kind, title in (("city", "Cities"), ("town", "Towns"), ("village", "Villages")):
        group = sorted((s for s in world.settlements if s.kind == kind), key=lambda s: -s.population)
        if not group:
            continue
        lines += [f"## {title}", "", "| Name | People | Coast | Land | Known for | Founded | Map position (km) |",
                  "|---|---:|---|---|---|---|---|"]
        for s in group:
            lines.append(f"| {s.name} | {s.population:,} | {'yes' if s.coastal else 'no'} | {s.biome} | "
                         f"{', '.join(s.known_for)} | {s.founded} | {s.x / 1000:.1f}, {s.y / 1000:.1f} |")
        lines.append("")
    for plan in plans:
        s = plan.settlement
        lines += [f"## {s.name} in detail", ""]
        kinds: dict = {}
        for d in plan.districts:
            kinds.setdefault(d.kind, []).append(d.name)
        for kind, names in sorted(kinds.items()):
            lines.append(f"- **{kind}**: {', '.join(sorted(names))}")
        marks = [m.name for m in plan.landmarks if m.kind == "mosque"]
        gates = [m.name for m in plan.landmarks if m.kind == "gate"]
        if marks:
            lines.append(f"- **mosques**: {', '.join(marks)}")
        if gates:
            lines.append(f"- **gates of the old town**: {', '.join(gates)}")
        kasbahs = [m.name for m in plan.landmarks if m.kind == "kasbah"]
        if kasbahs:
            lines.append(f"- **kasbah** (the citadel on the old town's high edge): {', '.join(kasbahs)}")
        civic = [m.name for m in plan.landmarks if m.kind in ("cathedral", "theatre")]
        if civic:
            lines.append(f"- **on the boulevard**: {', '.join(civic)}")
        stations = [m.name for m in plan.landmarks if m.kind == "station"]
        if stations and getattr(plan, "station", None) is not None:
            n = len(plan.station.tracks)
            lines.append(f"- **railway station** ({n} tracks, at the edge of the colonial quarter): {', '.join(stations)}")
        port = getattr(plan, "port", None)
        if port is not None:
            lights = [m.name for m in plan.landmarks if m.kind == "lighthouse"]
            quay = sum(q.line.length for q in port.quays)
            text = f"- **harbor**: {quay:,.0f} m of quays {port.level:g} m above the sea"
            if port.breakwaters:
                text += f", a breakwater of {sum(bw.line.length for bw in port.breakwaters):,.0f} m"
            if lights:
                text += f"; lighthouse: {', '.join(lights)}"
            lines.append(text)
        if plan.souks:
            seen = {}
            for k in plan.souks:
                seen.setdefault(k.name, k.trade)
            lines.append("- **souks**: " + ", ".join(f"{n} ({t})" for n, t in seen.items()))
        if plan.households:
            notable = sorted(plan.households, key=lambda h: -h.wealth)[:5]
            lines.append("- **notable families**: " + ", ".join(f"the {h.family} family ({h.trade}s)" for h in notable))
        st = plan.stats
        lines += [f"- **size**: {st['buildings']:,} buildings, {len(plan.households):,} households, "
                  f"{st['streets']:,} streets, {st['trees']:,} trees", ""]
    return "\n".join(lines) + "\n"


def _describe(s) -> str:
    coast = "on the coast" if s.coastal else "inland"
    known = f" Known for {', '.join(s.known_for)}." if s.known_for else ""
    founded = f" Founded in the time of {s.founded}." if s.founded else ""
    return (f"**{s.name}**, {s.population:,} people, {coast}, in {s.biome} country at {s.elevation:.0f} m."
            f"{founded}{known}")
