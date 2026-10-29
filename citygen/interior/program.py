"""The room program of an old-town house's floor 0 (SPEC 6c table): which cell is the bit, the kitchen, the
washroom and the store, once the cuts and merges have settled the cells.

Every dar and compact house keeps a bit, a matbakh and a bit el ma; when cells run short the bit el mouna
gives way first, then the maqsuras, then the bit el ma; the bit and the matbakh never do. A small house
keeps a bit, and a matbakh when floor 0 holds two rooms or more. A service never exceeds its `largest`
(`[interiors.dar] largest`): a bigger cell gives it one end, cut by `free_cut`, the rest stays a room.
"""
from __future__ import annotations

from .cuts import Frame, absorb, cut, shared, union, width

SERVICES = ("matbakh", "bit_el_ma", "bit_el_mouna")
FIXED = ("skifa", "droj", "wast_ed_dar", "well", "bortal", "stah", "menzah")   # cells the program leaves alone
CARVE = 0.7      # share of `largest` a service carved from a bigger cell takes


def is_t_room(c) -> bool:
    """The T room: the bit with its central door planned (on the court or its bortal)."""
    return c.type == "bit" and any(d[0] in ("court_door", "inner") for d in c.doors)


def living(cells: list) -> list:
    """The cells of floor 0 that are rooms of the program (not skifa, stair, court, gallery)."""
    return [c for c in cells if c.type not in FIXED]


def assign(job, cells: list, small: bool = False) -> list:
    """Types for the living cells of floor 0 (see the module doc); returns the cells (carving adds some)."""
    cells = list(cells)
    keep = [c for c in living(cells) if is_t_room(c)]
    free = [c for c in living(cells) if c not in keep]
    for c in free:
        c.type = ""
    bits = list(keep)
    if not bits and free:
        c = max(free, key=lambda c: (job.fits(c.poly, "bit"), c.part == "middle", c.poly.area))
        c.type = "bit"
        bits.append(c)
        free.remove(c)
    wanted = ("matbakh",) if small else SERVICES    # a small house's lone bit spares a matbakh corner if it can
    skifa = [c.poly for c in cells if c.type == "skifa"]
    taken: dict = {}
    for service in wanted:
        ref = taken.get("matbakh") if service == "bit_el_ma" else (skifa[0] if skifa and service == "matbakh" else None)
        got = place(job, cells, free, service, ref, bits)
        if got is None and service in ("matbakh", "bit_el_ma"):
            got = from_bit(job, cells, free, bits, service, ref)
        if got is not None:
            taken[service] = got.poly
    for c in [c for c in free if not c.type]:
        beside = any(shared(c.poly, b.poly) >= job.door + 2 * (job.clear + job.half) for b in bits)
        if beside and c.part in ("corner", "kbou_side") and job.fits(c.poly, "maqsura") and not small:
            c.type = "maqsura"
        elif job.fits(c.poly, "bit") or c.poly.area > job.largest.get("bit_el_mouna", 8.0):
            c.type = "maqsura" if beside and not small and not job.fits(c.poly, "bit") else "bit"
            if c.type == "bit":
                bits.append(c)
        else:
            c.type = "bit_el_mouna"
    if small and "matbakh" not in taken:              # no kitchen fits: floor 0 is one room, a bit
        cells = into_bit(cells, bits)
    cells = absorb(cells, job.minimums, FIXED + ("matbakh", "bit_el_ma"), job.piece, (), job.largest)   # leftovers
    for c in [c for c in cells if c.type == "maqsura"]:
        if not any(shared(c.poly, b.poly) > 0.5 for b in cells if b.type == "bit"):
            c.type = "bit"                            # a maqsura stands only beside its bit
    return cells


def place(job, cells: list, free: list, service: str, ref, bits: list):
    """The cell for one service among the free ones (carved to `largest` when bigger); None when none fits."""
    big = job.largest.get(service, 99.0)
    cands = [c for c in free if not c.type and job.fits(c.poly, service)]

    def key(c):
        off_main = c.part != "corner" or c.band != main_of(bits)
        near = round(c.poly.distance(ref), 1) if ref is not None else 0.0
        if service == "bit_el_mouna":                 # a store goes to a corner or short cell, the smallest
            return (c.poly.area > big, c.part == "middle", c.poly.area, near)
        return (c.poly.area > big, -off_main, c.part == "middle", near, c.poly.area)

    for c in sorted(cands, key=key):
        if c.poly.area <= big + 1e-6:
            c.type = service
            return c
        parts = carve(job, c, service, ref)
        if parts is None:
            continue
        mine, rest = parts
        c.poly, c.type = mine, service
        for p in rest:
            other = type(c)(p, "", c.band, c.part)
            cells.append(other)
            free.append(other)
        return c
    return None


def from_bit(job, cells: list, free: list, bits: list, service: str, ref):
    """No free cell holds the service: carve it from one end of a bit (the largest first, never the T room's
    kbou), the rest staying a bit at its minimum; None when no bit can spare it."""
    for b in sorted(bits, key=lambda b: (b.alcove is not None, is_t_room(b), -b.poly.area)):
        if b.alcove is not None:
            continue
        got = carve(job, b, service, ref)
        if got is None:
            continue
        mine, rest = got
        if len(rest) != 1 or not job.fits(rest[0], "bit"):
            continue
        b.poly = rest[0]
        c = type(b)(mine, service, b.band, b.part)
        cells.append(c)
        return c
    return None


def into_bit(cells: list, bits: list) -> list:
    """Every other living cell joins the bit it touches (a small house too small for a kitchen)."""
    for c in [c for c in living(cells) if c.type != "bit"]:
        for b in sorted(bits, key=lambda b: -shared(c.poly, b.poly)):
            merged = union(b.poly, c.poly) if shared(c.poly, b.poly) > 1e-3 else None
            if merged is not None:
                b.poly = merged
                cells = [x for x in cells if x is not c]
                break
    return cells


def main_of(bits: list) -> str | None:
    t = next((b for b in bits if is_t_room(b)), None)
    return None if t is None else t.band


def carve(job, c, service: str, ref):
    """(the service's end of cell c, the rest) cut across the cell's long axis by `free_cut`, the end
    nearest `ref` (the skifa for a kitchen), its area about `CARVE` x `largest`; None when no cut keeps
    both parts at their minimums and the service within `largest`."""
    big = job.largest.get(service, 99.0)
    least = job.minimums.get(service, (0.0, 0.0))[0]
    target = max(CARVE * big, least * 1.2)
    frames = getattr(job, "frames", {})
    fr = frames.get(c.band) or Frame.of(c.poly)       # across the band, so both parts keep the court wall
    for axis in (0, 1):
        t0, t1 = fr.bounds(c.poly)[axis], fr.bounds(c.poly)[axis + 2]
        ends = [(t0, 1.0), (t1, -1.0)]
        if ref is not None:
            ends.sort(key=lambda e: abs(fr.local(ref.centroid.coords[0])[axis] - e[0]))
        for end, sgn in ends:
            at = end + sgn * (t1 - t0) * target / c.poly.area
            pos = job.free(c.poly, fr, axis, at, [0])
            if pos is None:
                continue
            lo, hi = cut(c.poly, fr, axis, pos)
            mine, rest = (lo, hi) if sgn > 0 else (hi, lo)
            if len(mine) != 1 or not rest:
                continue
            if mine[0].area > big + 1e-6 or not job.fits(mine[0], service):
                continue
            if any(p.area < job.minimums.get("bit_el_mouna", (1.5, 0.9))[0] for p in rest):
                continue
            return mine[0], rest
    return None


def problems(interior) -> list:
    """The program rules `rooms.check` adds for old-town houses."""
    if interior.layout not in ("dar", "compact", "small"):
        return []
    rules = interior.rules
    program = interior.layout                         # a fallback already reports its real layout
    big = rules.get("largest", {})
    out = []
    floor0 = [r for r in interior.rooms if r.floor == 0 and r.type not in FIXED]
    types = {r.type for r in floor0}
    if "bit" not in types:
        out.append("floor 0 has no bit")
    if program == "small":
        if len(floor0) >= 2 and "matbakh" not in types:
            out.append("floor 0 has two rooms or more but no matbakh")
    else:
        if "matbakh" not in types:
            out.append("floor 0 has no matbakh")
        least = rules["minimums"].get("bit_el_ma", (0.0, 0.0))
        spare = [r for r in floor0 if r.type in ("bit_el_mouna", "maqsura") and r.polygon.area >= least[0]
                 and width(r.polygon) >= least[1]]
        if "bit_el_ma" not in types and spare:
            out.append("floor 0 has no bit el ma but a store or maqsura that should have given way")
    for r in interior.rooms:
        if r.type in SERVICES and r.type in big and r.polygon.area > big[r.type] + 0.01:
            out.append(f"the {r.type} {r.id} has {r.polygon.area:.1f} m2, over its largest {big[r.type]}")
        if r.type == "maqsura" and not any(o.type == "bit" and o.floor == r.floor and shared(r.polygon, o.polygon) > 0.5
                                           for o in interior.rooms):
            out.append(f"the maqsura {r.id} stands beside no bit")
    return out

