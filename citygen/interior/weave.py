"""Textile and painted-wood images of the home kit (prompt 52, SPEC 6d "Textures and materials").

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


MAKERS = {"klim_red": _klim, "klim_indigo": _klim, "mergoum": _mergoum, "zarbia": _zarbia, "hasira": _hasira,
          "ticking": _ticking, "painted": _painted, "sajjada": _sajjada, "mink": _mink}


def texture(name: str, seed: int, spec: dict | None = None) -> Image.Image:
    """The image `name` (one of `MAKERS`): the same pixels for the same seed and settings."""
    values = {**DEFAULTS, "pixels": 256, **(spec or {})}
    size = int(values["pixels"])
    value = np.clip(MAKERS[name](stream(seed, "texture", name), size, values), 0.0, 1.0)
    return Image.fromarray((value * 255.0 + 0.5).astype(np.uint8), "RGB")


@lru_cache(maxsize=32)
def _encoded(name: str, seed: int, spec_items: tuple) -> Encoded:
    return encode(texture(name, seed, dict(spec_items)))


def encoded(name: str, seed: int, spec: dict | None = None) -> Encoded:
    """File bytes, MIME type and extension of one image; cached per process and settings."""
    return _encoded(name, seed, tuple(sorted((spec or {}).items())))
