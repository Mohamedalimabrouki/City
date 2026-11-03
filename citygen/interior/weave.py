"""Textile, painted-wood, book and goods images of the home kit (prompts 52 and 53, SPEC 6d "Textures and materials").

256 px colored images that tile seamlessly, like `mesh/textures._zellige` (the palette entry naming one is
white: the image holds the colors). Each draws only on `stream(seed, "texture", name)`; its numbers and
colours come from `[interiors.textures]`. `export.used_images` asks `MAKERS` before `mesh/textures`.

Rugs that show one repeat per rug (klim, mergoum, zarbia, sajjada) are drawn in rug space: the image's
columns run across the rug, its rows along it, so a motif `w` px wide and `h` px tall covers
w / 256 x W by h / 256 x D meters. Their borders meet at the image's edges, so they tile too.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from PIL import Image

from ..mesh.textures import DEFAULTS, Encoded, _WrapCanvas, _blur, _hex, _noise, encode
from ..rng import stream


def _col(s: dict, key: str, default: str = "#808080") -> np.ndarray:
    return _hex(str(s.get(key, default)))


def _paint(out: np.ndarray, mask: np.ndarray, color: np.ndarray) -> np.ndarray:
    return np.where(mask[:, :, None], color, out)


def _grid(n: int):
    y, x = np.mgrid[0:n, 0:n] + 0.5
    return x, y


def _woven(rng, out: np.ndarray, s: dict, pitch: float = 2.0) -> np.ndarray:
    """Wool texture over a flat design: weft ribs (a soft row stripe every `pitch` px) and mottle."""
    n = out.shape[0]
    _x, y = _grid(n)
    rib = 1.0 - 0.06 * float(s.get("rib", 1.0)) * (0.5 + 0.5 * np.cos(2 * np.pi * y / pitch))
    tone = 1.0 + 0.10 * s["mottle"] * (_noise(rng, n, 8, 3) - 0.5) * 2.0
    return out * (rib * tone)[:, :, None]


def _stepped(dx, dy, step: float):
    """Coordinates snapped to `step` px blocks: the stairs of a woven diagonal."""
    return np.floor(np.abs(dx) / step) * step, np.floor(np.abs(dy) / step) * step


def _klim(rng, n: int, s: dict) -> np.ndarray:
    """Flat-woven klim (one repeat per rug): a field colour crossed by bands of stepped diamonds, of
    triangles and of combs in the second colour, ochre, black and cream, thin stripes between them, the
    band order drawn on the image's stream."""
    x, y = _grid(n)
    field, second, ochre, black, cream = (_col(s, k) for k in ("field", "second", "ochre", "black", "cream"))
    out = np.ones((n, n, 3)) * field
    kinds = ["diamonds", "triangles", "combs", "diamonds"]
    order = [kinds[k] for k in rng.permutation(len(kinds))]
    band = n / len(order)
    step = float(s.get("step", 4))
    for b, kind in enumerate(order):
        c = (b + 0.5) * band
        dy = y - c
        for off, col in ((-0.42, cream), (-0.37, black), (0.37, black), (0.42, cream)):
            out = _paint(out, np.abs(dy - off * band) < 1.6, col)
        if kind == "diamonds":
            count = int(s.get("diamonds", 5))
            w = n / count
            dx = (x % w) - w / 2
            ax, ay = _stepped(dx, dy, step)
            d = ax / (w * 0.5) + ay / (band * 0.30)
            out = _paint(out, d < 1.0, second)
            out = _paint(out, d < 0.72, cream)
            out = _paint(out, d < 0.48, black if b % 2 else ochre)
            out = _paint(out, d < 0.2, second)
            hook = (np.abs(dy) < step) & (np.abs(np.abs(dx) - w * 0.5) < step * 1.5)
            out = _paint(out, hook, ochre)
        elif kind == "triangles":
            count = int(s.get("triangles", 9))
            w = n / count
            dx = (x % w) - w / 2
            ax, _ay = _stepped(dx, 0.0 * dx, step)
            top = c + band * 0.25 - ax * (band * 0.5 / (w * 0.5))
            tri = (y > c - band * 0.25) & (y < top)
            out = _paint(out, tri, black)
            out = _paint(out, tri & (ax < w * 0.22) & (y > c - band * 0.12), ochre)
            down = (y < c - band * 0.25 + 3) & (y > c - band * 0.25) | (np.abs(y - (c + band * 0.27)) < 1.5)
            out = _paint(out, down, cream)
        else:   # combs: a bar with teeth, in two rows facing each other
            count = int(s.get("combs", 16))
            w = n / count
            dx = (x % w) - w / 2
            out = _paint(out, np.abs(dy) < 2.0, cream)
            teeth = (np.abs(dx) < w * 0.18) & (np.abs(dy) > 2.0) & (np.abs(dy) < band * 0.22)
            out = _paint(out, teeth & (dy < 0), second)
            out = _paint(out, teeth & (dy > 0), ochre)
            for k in (-1, 1):
                out = _paint(out, np.abs(dy - k * band * 0.27) < 1.5, black)
    return _woven(rng, out, s)


def _mergoum(rng, n: int, s: dict) -> np.ndarray:
    """Mergoum (one repeat per rug): fine weft-wrapped lozenges with hooks, rows of them offset by half a
    lozenge, in black and white on red, between bands of small chevrons; a black and white edge."""
    x, y = _grid(n)
    field, black, white = (_col(s, k) for k in ("field", "black", "white"))
    accent = _col(s, "accent", "#C9962E")
    out = np.ones((n, n, 3)) * field
    rows = int(s.get("rows", 8))
    across = int(s.get("across", 6))
    h, w = n / rows, n / across
    r = np.floor(y / h)
    dy = (y % h) - h / 2
    dx = ((x + (r % 2) * w / 2) % w) - w / 2
    ax, ay = _stepped(dx, dy, 2.0)
    d = ax / (w * 0.42) + ay / (h * 0.40)
    out = _paint(out, (d < 1.0) & (d > 0.78), black)
    out = _paint(out, (d < 0.62) & (d > 0.42), white)
    out = _paint(out, d < 0.22, np.where((r % 2)[..., None] > 0, accent, black))
    hook = (np.abs(ay) < 2.0) & (np.abs(ax - w * 0.46) < 3.0)
    out = _paint(out, hook, white)
    out = _paint(out, (np.abs(dy) > h * 0.46) & (np.floor(x / 4) % 2 == 0), black)   # dotted lines between rows
    edge = np.minimum(x, n - x)
    out = _paint(out, edge < n * 0.035, black)
    out = _paint(out, (edge < n * 0.02) & (np.floor(y / 4) % 2 == 0), white)
    return _woven(rng, out, s, 1.5)


def _zarbia(rng, n: int, s: dict) -> np.ndarray:
    """The knotted Kairouan carpet (one repeat per rug): a stepped lozenge medallion with its pendants in
    a cream field of small motifs, inside a wide brown border with an indigo running motif."""
    x, y = _grid(n)
    field, brown, indigo, red = (_col(s, k) for k in ("field", "brown", "indigo", "red"))
    out = np.ones((n, n, 3)) * field
    bw = n * float(s.get("border", 0.13))
    edge = np.minimum(np.minimum(x, n - x), np.minimum(y, n - y))
    cx, cy = x - n / 2, y - n / 2
    ax, ay = _stepped(cx, cy, 3.0)
    d = ax / (n * 0.30) + ay / (n * 0.36)
    small = ((np.abs((x % 16) - 8) + np.abs((y % 16) - 8)) < 3) & ((np.floor(x / 16) + np.floor(y / 16)) % 2 == 0)
    out = _paint(out, small, brown)
    out = _paint(out, d < 1.0, indigo)
    out = _paint(out, d < 0.9, field)
    out = _paint(out, d < 0.8, red)
    out = _paint(out, d < 0.55, field)
    out = _paint(out, d < 0.42, brown)
    out = _paint(out, d < 0.18, indigo)
    pend = (np.abs(cx) < 3 + 0.0 * cy) & (np.abs(cy) > n * 0.36) & (np.abs(cy) < n * 0.42)
    out = _paint(out, pend, indigo)
    corner = (np.abs(np.abs(cx) - n * 0.30) + np.abs(np.abs(cy) - n * 0.32)) < n * 0.06
    out = _paint(out, corner & (edge > bw), red)
    border = edge < bw
    out = _paint(out, border, brown)
    t = np.where(np.minimum(x, n - x) < np.minimum(y, n - y), y, x)   # along the border
    run = (np.abs((t % 20) - 10) + np.abs(edge - bw * 0.5)) < bw * 0.32
    out = _paint(out, border & run, indigo)
    out = _paint(out, border & (np.abs(edge - bw * 0.88) < 1.5), field)
    out = _paint(out, edge < 2.5, indigo)
    knots = 1.0 + 0.08 * s["mottle"] * (_noise(rng, n, 16, 2) - 0.5) * 2.0
    return out * knots[:, :, None]


def _hasira(rng, n: int, s: dict) -> np.ndarray:
    """The halfa mat: rows of plaited straw strands slanting one way then the other in alternating bands,
    with a few dyed bands, each strand a little lighter or darker."""
    x, y = _grid(n)
    straw, dark, dyed = (_col(s, k) for k in ("straw", "dark", "dyed"))
    bands = int(s.get("bands", 8))
    h = n / bands
    b = np.floor(y / h)
    slant = np.where(b % 2 == 0, 1.0, -1.0)
    pitch = n / round(n / float(s.get("pitch", 6)))          # a whole number of strands across: it wraps
    t = (x + slant * (y % h)) / pitch
    strand = np.floor(t)
    tone = 0.85 + 0.3 * rng.random(int(n / pitch) + 2)[(strand % int(n / pitch)).astype(np.int64)]
    shade = 0.82 + 0.18 * np.sin(np.pi * (t % 1.0))
    out = straw * (tone * shade)[:, :, None]
    dyed_band = (b % 4 == 1)
    out = np.where(dyed_band[:, :, None], dyed * (tone * shade)[:, :, None], out)
    out = _paint(out, ((y % h) < 1.0) | ((y % h) > h - 1.0), dark)   # the seam between bands, centred on it
    return out * (1.0 + 0.05 * s["mottle"] * (_noise(rng, n, 8, 2) - 0.5) * 2.0)[:, :, None]


def _ticking(rng, n: int, s: dict) -> np.ndarray:
    """Mattress ticking: narrow red and blue stripes on cream, running along the rows."""
    _x, y = _grid(n)
    cream, red, blue = (_col(s, k) for k in ("cream", "red", "blue"))
    rep = n / int(s.get("repeats", 8))
    t = y % rep
    out = np.ones((n, n, 3)) * cream
    for a, b, c in ((6, 9, red), (11, 12.5, blue), (14.5, 16, blue), (rep / 2 + 8, rep / 2 + 9.5, red)):
        out = _paint(out, (t >= a) & (t < b), c)
    return _woven(rng, out, s, 1.0)


def _flowers(rng, n: int, count: int, rmin: float, rmax: float, petals: int):
    """Wrapped masks of painted flowers: petals, hearts and leaves, at random spots (seamless)."""
    petal, heart, leaf = _WrapCanvas(n), _WrapCanvas(n), _WrapCanvas(n)
    for _ in range(count):
        x, y = rng.uniform(0.0, n, 2)
        r = rng.uniform(rmin, rmax)
        turn = rng.uniform(0.0, 2 * np.pi)
        for k in range(2):
            a = turn + np.pi * 0.75 + k * np.pi * 0.5
            leaf.ellipse(x + np.cos(a) * r * 1.5, y + np.sin(a) * r * 1.5, r * 0.75, r * 0.38, 255)
        for k in range(petals):
            a = turn + k * 2 * np.pi / petals
            petal.ellipse(x + np.cos(a) * r * 0.6, y + np.sin(a) * r * 0.6, r * 0.45, r * 0.45, 255)
        heart.ellipse(x, y, r * 0.3, r * 0.3, 255)
    return petal.mask() > 0.5, heart.mask() > 0.5, leaf.mask() > 0.5


def _painted(rng, n: int, s: dict) -> np.ndarray:
    """The painted wood of Tunis chests and beds: red and yellow flowers with white hearts and leaves on
    a green ground, a little worn."""
    ground, red, yellow, white, leafc = (_col(s, k) for k in ("ground", "red", "yellow", "white", "leaf"))
    out = np.ones((n, n, 3)) * ground
    petal, heart, leaf = _flowers(rng, n, int(s.get("flowers", 9)), n * 0.05, n * 0.08, 5)
    out = _paint(out, leaf, leafc)
    pick = _blur(_noise(rng, n, 4, 1), 2.0) > 0.5
    out = _paint(out, petal & pick, red)
    out = _paint(out, petal & ~pick, yellow)
    out = _paint(out, heart, white)
    wear = 1.0 + 0.10 * s["mottle"] * (_noise(rng, n, 8, 3) - 0.5) * 2.0
    return out * wear[:, :, None]


def _sajjada(rng, n: int, s: dict) -> np.ndarray:
    """A prayer mat (one repeat per mat): a pointed mihrab arch over a plain field, its head end at the
    image's first rows, inside a border."""
    x, y = _grid(n)
    field, arch, border, line = (_col(s, k) for k in ("field", "arch", "border", "line"))
    out = np.ones((n, n, 3)) * arch
    bw = n * 0.09
    edge = np.minimum(np.minimum(x, n - x), np.minimum(y, n - y))
    cx = x - n / 2
    half = n / 2 - bw * 2.2
    r = half * float(s.get("point", 1.15))                         # two arcs of radius r meet in the point
    rise = np.sqrt(r * r - (r - half) ** 2)
    spring = bw * 1.8 + rise                                      # where the arch springs, from the head end
    foot = n - bw * 1.8

    def inside(m: float):
        arc = np.hypot(np.abs(cx) + (r - half), y - spring) < r - m
        return (np.abs(cx) < half - m) & ((y > spring) | arc) & (y < foot - m)

    out = _paint(out, inside(0.0), line)
    out = _paint(out, inside(3.0), field)
    chain = (np.abs(cx) < 1.2) & (y > spring - rise + 4) & (y < spring - n * 0.08)
    lamp = (np.abs(cx) < 7 - 0.25 * np.abs(y - (spring - n * 0.05))) & (np.abs(y - (spring - n * 0.05)) < n * 0.035)
    out = _paint(out, chain | lamp, line)
    out = _paint(out, edge < bw, border)
    along = np.where(np.minimum(x, n - x) < np.minimum(y, n - y), y, x)
    out = _paint(out, (edge < bw) & (np.abs(((along + edge) % 8) - 4) < 1.5), line)   # chevrons that meet at the edges
    out = _paint(out, np.abs(edge - bw) < 1.2, line)
    return _woven(rng, out, s, 1.5)


def _mink(rng, n: int, s: dict) -> np.ndarray:
    """The plush mink blanket: big roses in two shades with leaves on a deep ground, soft-edged."""
    ground, rose, rose2, leafc = (_col(s, k) for k in ("ground", "rose", "rose_2", "leaf"))
    out = np.ones((n, n, 3)) * ground
    petal, heart, leaf = _flowers(rng, n, int(s.get("flowers", 4)), n * 0.10, n * 0.15, 7)
    soft = lambda m: _blur(m.astype(np.float64), 1.6)[:, :, None]   # noqa: E731
    out = out * (1 - soft(leaf)) + leafc * soft(leaf)
    out = out * (1 - soft(petal)) + rose * soft(petal)
    out = out * (1 - soft(heart)) + rose2 * soft(heart)
    plush = 1.0 + 0.12 * s["mottle"] * (_noise(rng, n, 32, 2) - 0.5) * 2.0
    return out * plush[:, :, None]


def _rug_floral(rng, n: int, s: dict) -> np.ndarray:
    """The machine-made rug of modern salons (one repeat per rug): a red field strewn with small flowers,
    a navy medallion with a cream ring and a red heart, navy corner pieces, and a wide navy border of
    rosettes between cream guard lines (its rosettes repeat every 32 px, so the border meets itself)."""
    x, y = _grid(n)
    field, navy, guard, flower, leafc, rose = (_col(s, k) for k in ("field", "navy", "guard", "flower", "leaf", "rose"))
    out = np.ones((n, n, 3)) * field
    bw = n * float(s.get("border", 0.12))
    edge = np.minimum(np.minimum(x, n - x), np.minimum(y, n - y))
    petal, heart, leaf = _flowers(rng, n, int(s.get("flowers", 60)), n * 0.022, n * 0.034, 6)
    field_zone = edge > bw + 3
    out = _paint(out, leaf & field_zone, leafc)
    out = _paint(out, petal & field_zone, flower)
    out = _paint(out, heart & field_zone, rose)
    m = (np.abs(x - n / 2) / (n * 0.20)) ** 1.4 + (np.abs(y - n / 2) / (n * 0.28)) ** 1.4   # the medallion
    out = _paint(out, m < 1.0, navy)
    out = _paint(out, (m > 0.78) & (m < 0.88), guard)
    out = _paint(out, m < 0.45, rose)
    out = _paint(out, m < 0.18, guard)
    corner = np.hypot(np.minimum(x, n - x) - bw, np.minimum(y, n - y) - bw) < n * 0.13
    out = _paint(out, corner & field_zone, navy)
    out = _paint(out, edge < bw, navy)
    along = np.where(np.minimum(x, n - x) < np.minimum(y, n - y), y, x)
    ros = np.hypot(((along % 32) - 16), edge - bw / 2)
    out = _paint(out, (edge < bw) & (ros < bw * 0.32), rose)
    out = _paint(out, (edge < bw) & (ros < bw * 0.12), guard)
    out = _paint(out, (np.abs(edge - bw) < 1.3) | (np.abs(edge - bw * 0.15) < 1.0), guard)
    return _woven(rng, out, s, 2.0)


def _items(rng, n: int, lo: float, hi: float) -> list:
    """Column edges of items side by side across the image: widths drawn between lo and hi px, scaled
    so the last edge is the image's (the columns wrap at an item's edge)."""
    widths = []
    while sum(widths) < n:
        widths.append(float(rng.uniform(lo, hi)))
    edges = np.round(np.cumsum([0.0] + widths) * n / sum(widths)).astype(int)
    return [(int(a), int(b)) for a, b in zip(edges[:-1], edges[1:]) if b > a]


def _palette(s: dict) -> list:
    return [_hex(str(s[k])) for k in sorted(s) if k.startswith("color_")]


def _spines(rng, n: int, s: dict) -> np.ndarray:
    """Book backs standing on a shelf (one row per image, its top the row's top): widths and heights drawn
    on the stream, cloth colours, a gold band or two on some, a pale label on others, each back rounded by
    its shading, the dark of the shelf above the shorter ones."""
    x, y = _grid(n)
    colors = _palette(s)
    gold, label = _col(s, "gold"), _col(s, "label")
    out = np.ones((n, n, 3)) * _col(s, "gap")
    for x0, x1 in _items(rng, n, float(s.get("wmin", 7)), float(s.get("wmax", 20))):
        top = n * (1.0 - float(rng.uniform(float(s.get("hmin", 0.7)), 0.98)))
        col = colors[int(rng.integers(len(colors)))] * float(rng.uniform(0.8, 1.1))
        inside = (x >= x0) & (x < x1 - 0.5) & (y >= top)
        tone = 1.0 - 0.35 * ((x - (x0 + x1) / 2) / max((x1 - x0) / 2, 1.0)) ** 2
        book = col * tone[:, :, None]
        kind = int(rng.integers(3))
        span = n - top
        if kind == 0:
            for f in (0.10, 0.85):
                book = np.where((np.abs(y - (top + span * f)) < 1.6)[:, :, None], gold * tone[:, :, None], book)
        elif kind == 1:
            book = np.where(((y > top + span * 0.25) & (y < top + span * 0.50) & (x > x0 + 2) & (x < x1 - 2.5))[:, :, None],
                            label * tone[:, :, None], book)
        out = np.where(inside[:, :, None], book, out)
    grain = 1.0 + 0.08 * s["mottle"] * (_noise(rng, n, 16, 2) - 0.5) * 2.0
    return out * grain[:, :, None]


GOODS_KINDS = ("box", "tin", "bottle", "jar", "packet", "stack")


def _goods(rng, n: int, s: dict, seed: int = 0) -> np.ndarray:
    """`rows` shelf rows of a Tunisian grocer's goods, one under the other (kit_new.TEX_H: one row's v
    size), so the shelves of a piece need not repeat one row: the first row drawn on the image's stream,
    each further row k on its own (seed, "texture", "goods", "row", k), the mottle over all of them."""
    rows = max(int(s.get("rows", 1)), 1)
    h = n // rows
    bands = [_goods_row(rng if k == 0 else stream(seed, "texture", "goods", "row", k), n, h, s) for k in range(rows)]
    out = np.concatenate(bands + [bands[-1][: n - h * rows]], axis=0)
    grain = 1.0 + 0.06 * s["mottle"] * (_noise(rng, n, 16, 2) - 0.5) * 2.0
    return out * grain[:, :, None]


def _fleece(rng, n: int, s: dict) -> np.ndarray:
    """A sheepskin's wool: crimped locks (rings of a tiled noise field), warm cream on their crowns and a
    darker honey in the hollows between them."""
    cream, hollow = _col(s, "cream"), _col(s, "hollow")
    locks = _noise(rng, n, int(s.get("locks", 16)), 2)
    crimp = 0.5 + 0.5 * np.sin(2 * np.pi * float(s.get("crimp", 5)) * locks)
    t = np.clip(crimp ** 0.5 * (0.75 + 0.5 * (_noise(rng, n, 8, 2) - 0.5) * 2.0 * s["mottle"]), 0.0, 1.0)
    return hollow + (cream - hollow) * t[:, :, None]


def _net(rng, n: int, s: dict) -> np.ndarray:
    """A fishing net in a heap: diamond meshes of cords with a knot at each crossing, the folds below
    showing dark through the holes."""
    x, y = _grid(n)
    cord, knot, gap = _col(s, "cord"), _col(s, "knot"), _col(s, "gap")
    p = n / int(s.get("cells", 16))                          # a whole number of meshes across: it wraps
    u, v = (x + y) / p, (x - y) / p
    du, dv = np.abs(u - np.round(u)) * p, np.abs(v - np.round(v)) * p
    half = float(s.get("cord_width", 2.0)) / 2
    out = np.broadcast_to(gap, (n, n, 3)) * (0.8 + 0.4 * _noise(rng, n, 4, 2))[:, :, None]
    tone = 0.85 + 0.3 * s["mottle"] * _noise(rng, n, 8, 2)
    out = np.where(((du < half) | (dv < half))[:, :, None], cord * tone[:, :, None], out)
    return _paint(out, (du < half * 1.6) & (dv < half * 1.6), knot)


def _goods_row(rng, n: int, hh: int, s: dict) -> np.ndarray:
    """One shelf row of goods, n px wide and hh tall, in facings of two to four of a product on the row's
    foot, near the row's full height: cartons (tea, sugar, milk) with a shaded side and a coloured stripe
    on a pale panel, tomato-paste tins two high with light rims and a wrap label, stacks of four flat tins
    (sardines, tuna), oil and water bottles with shoulders, a neck and a cap, harissa jars two high under
    a metal lid, soft packets (couscous, pasta) with a crimped seal; each product a body and an accent
    colour of the palette, the dark of the shelf's back between them (a gap at each edge, so the row
    tiles across)."""
    y, x = np.mgrid[0:hh, 0:n] + 0.5
    colors = _palette(s)
    label, cap = _col(s, "label"), _col(s, "cap")
    weights = np.array([float(s.get(f"w_{k}", 1.0)) for k in GOODS_KINDS])
    cuts = np.cumsum(weights / weights.sum())[:-1]
    out = np.ones((hh, n, 3)) * _col(s, "back")
    run, left = [], 0
    stacked = {"tin": int(s.get("tins_high", 2)), "stack": int(s.get("flat_high", 4)), "jar": int(s.get("jars_high", 2))}
    for x0, x1 in _items(rng, n, float(s.get("wmin", 14)), float(s.get("wmax", 34))):
        if left <= 0:      # a new product
            kind = GOODS_KINDS[int(np.searchsorted(cuts, rng.uniform()))]
            i, j = rng.choice(len(colors), 2, replace=False)
            run = [kind, colors[int(i)], colors[int(j)], float(rng.uniform(float(s.get("hmin", 0.5)), float(s.get("hmax", 0.92))))]
            left = int(rng.integers(int(s.get("facing_min", 2)), int(s.get("facing_max", 4)) + 1))
        left -= 1
        kind, col, acc, hf = run
        a, b = x0 + 1, x1 - 1
        top = hh * (1.0 - hf)
        cx, half = (a + b) / 2, max((b - a) / 2, 1.0)
        u = (x - cx) / half
        span = hh - top
        round_ = (1.0 - 0.38 * u ** 2)[:, :, None]
        if kind == "box":
            tone = np.where((u > 0.55)[:, :, None], 0.78, 1.0) * np.ones((n, n, 1))
            item = (x >= a) & (x < b) & (y >= top)
            out = np.where(item[:, :, None], col * tone, out)
            panel = item & (y > top + span * 0.18) & (y < top + span * 0.62) & (u < 0.50) & (u > -0.80)
            out = np.where(panel[:, :, None], label * tone, out)
            out = np.where((panel & (y > top + span * 0.30) & (y < top + span * 0.42))[:, :, None], acc * tone, out)
            out = np.where((item & (np.abs(y - top - 1.5) < 1.0))[:, :, None], col * tone * 0.75, out)
        elif kind in ("tin", "stack"):
            k = stacked[kind]
            for t0, t1 in ((top + span * i / k, top + span * (i + 1) / k) for i in range(k)):
                item = (x >= a) & (x < b) & (y >= t0) & (y < t1)
                h = t1 - t0
                out = np.where(item[:, :, None], label * round_, out)
                out = np.where((item & (y > t0 + h * 0.22) & (y < t0 + h * 0.80))[:, :, None], col * round_, out)
                out = np.where((item & (np.abs(u) < 0.45) & (y > t0 + h * 0.38) & (y < t0 + h * 0.62))[:, :, None],
                               acc * round_, out)
                out = np.where((item & ((y < t0 + 2.0) | (y > t1 - 2.0)))[:, :, None], cap * round_, out)
        elif kind == "bottle":
            shoulder, neck = top + span * 0.30, top + span * 0.14
            w = np.where(y >= shoulder, 1.0, 0.38 + 0.62 * np.clip((y - neck) / max(shoulder - neck, 1.0), 0, 1))
            body = (np.abs(u) < w) & (y >= top + 3)
            out = np.where(body[:, :, None], col * round_, out)
            band = body & (y > top + span * 0.52) & (y < top + span * 0.80)
            out = np.where(band[:, :, None], label * round_, out)
            out = np.where((band & (np.abs(u) < 0.5) & (y > top + span * 0.60) & (y < top + span * 0.70))[:, :, None],
                           acc * round_, out)
            out = np.where(((np.abs(u) < 0.36) & (y >= top) & (y < top + 4))[:, :, None], acc * round_ * 0.85, out)
            out = np.where((body & (np.abs(u + 0.45) < 0.10) & (y > shoulder))[:, :, None], np.minimum(col * 1.35 + 0.1, 1.0), out)
        elif kind == "jar":
            k = stacked[kind]
            for t0 in (top + span * i / k for i in range(k)):
                sp = span / k
                item = (x >= a) & (x < b) & (y >= t0 + 4) & (y < t0 + sp)
                out = np.where(item[:, :, None], col * round_, out)
                out = np.where((item & (y > t0 + sp * 0.35) & (y < t0 + sp * 0.80))[:, :, None], label * round_, out)
                out = np.where((item & (np.abs(u) < 0.55) & (y > t0 + sp * 0.48) & (y < t0 + sp * 0.66))[:, :, None],
                               acc * round_, out)
                out = np.where(((np.abs(u) < 0.92) & (y >= t0) & (y < t0 + 4))[:, :, None], cap * round_ * 0.9, out)
        else:              # a soft packet: narrower to its crimped seal, a pale window
            w = 0.84 + 0.16 * np.clip((y - top) / max(span * 0.25, 1.0), 0, 1)
            seal = (np.abs(u) < 0.84) & (y >= top) & (y < top + 4 + 1.5 * (np.floor(x / 2) % 2))
            item = (np.abs(u) < w) & (y >= top + 4)
            soft = (1.0 - 0.22 * u ** 2 - 0.06 * np.sin((y - top) * 0.6) * (np.abs(u) > 0.6))[:, :, None]
            out = np.where((item | seal)[:, :, None], col * soft, out)
            win = item & (np.abs(u) < 0.55) & (y > top + span * 0.35) & (y < top + span * 0.70)
            out = np.where(win[:, :, None], label * soft, out)
            out = np.where((win & (y > top + span * 0.42) & (y < top + span * 0.52))[:, :, None], acc * soft, out)
    return out


MAKERS = {"klim_red": _klim, "klim_indigo": _klim, "mergoum": _mergoum, "zarbia": _zarbia, "hasira": _hasira,
          "ticking": _ticking, "painted": _painted, "sajjada": _sajjada, "mink": _mink,
          "rug_floral": _rug_floral, "spines": _spines, "goods": _goods, "fleece": _fleece, "net": _net}
SEEDED = ("goods",)     # makers that open their own further streams of the seed


def texture(name: str, seed: int, spec: dict | None = None) -> Image.Image:
    """The image `name` (one of `MAKERS`): the same pixels for the same seed and settings."""
    values = {**DEFAULTS, "pixels": 256, **(spec or {})}
    size = int(values["pixels"])
    rng = stream(seed, "texture", name)
    value = np.clip(MAKERS[name](rng, size, values, seed) if name in SEEDED else MAKERS[name](rng, size, values), 0.0, 1.0)
    return Image.fromarray((value * 255.0 + 0.5).astype(np.uint8), "RGB")


@lru_cache(maxsize=32)
def _encoded(name: str, seed: int, spec_items: tuple) -> Encoded:
    return encode(texture(name, seed, dict(spec_items)))


def encoded(name: str, seed: int, spec: dict | None = None) -> Encoded:
    """File bytes, MIME type and extension of one image; cached per process and settings."""
    return _encoded(name, seed, tuple(sorted((spec or {}).items())))
