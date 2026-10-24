"""Generated base-color textures for the 3D materials (prompt 18).

A palette entry may name a texture (`texture = "plaster"`) and the size in meters one repeat
covers (`texture_size = [3.0, 3.0]`). The .glb writer turns that into a base-color texture with
`KHR_texture_transform`, so the meter UVs of every mesh keep working unchanged.

Every image is square, seamless (all noise wraps at the edges) and near-neutral grey around
white: the palette color multiplies the texture (glTF `baseColorFactor` x `baseColorTexture`),
so one plaster image serves every wall color. Nothing here paints windows, doors or palette
colors.

Each texture owns its random stream (`stream(seed, "texture", name)`), so adding or reworking one
surface never changes another. Numbers (pixel size, noise strengths) live in the `[textures]`
table of the style (`styles/<style>.toml`); `texture(name, seed)` uses the built-in defaults.
Images are encoded as PNG or JPEG, whichever is smaller.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from ..noise import smoothstep
from ..rng import stream

PIXELS = (256, 512)   # allowed image sides (see the [textures] table)

# Wall, roof and ground surfaces, in the order the texture sheet shows them.
NAMES = ("plaster", "render", "render_cream", "stone", "concrete",
         "roof_tile", "roof_flat", "paving", "asphalt", "earth", "sand", "grass",
         "rock", "scrub", "ballast")

# Fallbacks when the style does not name a value; the style table wins.
DEFAULTS = {"pixels": 512, "grain": 0.45, "mottle": 0.4, "stain": 0.35, "band": 0.6}


@dataclass(frozen=True)
class Encoded:
    """One image file: its bytes, MIME type and extension."""
    data: bytes
    mime: str
    ext: str


# --- small tileable-noise helpers -------------------------------------------------

def _upsample(lattice: np.ndarray, size: int) -> np.ndarray:
    """Smooth periodic interpolation of a small square lattice of random values."""
    cells = lattice.shape[0]
    t = np.arange(size, dtype=np.float64) * (cells / size)
    base = np.floor(t)
    f = t - base
    i0 = base.astype(np.int64) % cells
    i1 = (i0 + 1) % cells
    s = f * f * (3.0 - 2.0 * f)
    rows = lattice[:, i0] * (1.0 - s) + lattice[:, i1] * s
    return rows[i0, :] * (1.0 - s)[:, None] + rows[i1, :] * s[:, None]


def _noise(rng, size: int, cells: int = 4, octaves: int = 4, gain: float = 0.55) -> np.ndarray:
    """Fractal value noise in [0, 1] that wraps at every edge."""
    total = np.zeros((size, size), dtype=np.float64)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        total += amp * _upsample(rng.random((cells << o, cells << o)), size)
        norm += amp
        amp *= gain
    return total / norm


def _line_noise(rng, size: int, cells: int = 4, octaves: int = 3) -> np.ndarray:
    """The same idea in one dimension: smooth noise across x, the same for every row."""
    total = np.zeros(size, dtype=np.float64)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        c = cells << o
        values = rng.random(c)
        t = np.arange(size, dtype=np.float64) * (c / size)
        base = np.floor(t)
        f = t - base
        i0 = base.astype(np.int64) % c
        i1 = (i0 + 1) % c
        s = f * f * (3.0 - 2.0 * f)
        total += amp * (values[i0] * (1.0 - s) + values[i1] * s)
        norm += amp
        amp *= 0.5
    return total / norm


def _blur(a: np.ndarray, radius: float) -> np.ndarray:
    """Gaussian blur that wraps (a Fourier blur, so the edges join exactly)."""
    if radius < 0.25:
        return a
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    kernel = np.exp(-2.0 * (np.pi * radius) ** 2 * (fx ** 2 + fy ** 2))
    return np.fft.irfft2(np.fft.rfft2(a) * kernel, s=(h, w))


def _stains(rng, size: int, cells: int = 3, octaves: int = 3,
            radius: float | None = None) -> np.ndarray:
    """Soft, irregular 0-1 patches: damp marks, lichen, worn paint."""
    a = _noise(rng, size, cells, octaves)
    return smoothstep(0.52, 0.70, _blur(a, size / 64.0 if radius is None else radius))


class _WrapCanvas:
    """A stroke mask that wraps: every stroke is drawn at nine offsets."""

    def __init__(self, size: int):
        self.size = size
        self.img = Image.new("L", (3 * size, 3 * size), 0)
        self.draw = ImageDraw.Draw(self.img)

    def _copies(self, xy):
        s = self.size
        for dx, dy in ((0, 0), (-s, 0), (s, 0), (0, -s), (0, s),
                       (-s, -s), (-s, s), (s, -s), (s, s)):
            yield [(x + s + dx, y + s + dy) for x, y in xy]

    def line(self, xy, value: int, width: int = 1) -> None:
        for pts in self._copies(xy):
            self.draw.line(pts, fill=int(np.clip(value, 0, 255)), width=width)

    def ellipse(self, x: float, y: float, rx: float, ry: float, value: int) -> None:
        s = self.size
        for dx in (-s, 0, s):
            for dy in (-s, 0, s):
                cx, cy = x + s + dx, y + s + dy
                self.draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=int(value))

    def mask(self) -> np.ndarray:
        s = self.size
        return np.asarray(self.img.crop((s, s, 2 * s, 2 * s)), dtype=np.float64) / 255.0


def _cracks(canvas: _WrapCanvas, rng, n: int, count: int, steps=(4, 12), value: int = 150,
            width: int = 1) -> None:
    """Random-walk hairline cracks; a jump across an edge starts a new wrapped segment."""
    for _ in range(count):
        x, y = rng.uniform(0.0, n, 2)
        angle = rng.uniform(0.0, 2.0 * np.pi)
        pts = [(x, y)]
        for _ in range(int(rng.integers(*steps))):
            angle += rng.normal(0.0, 0.45)
            step = rng.uniform(3.0, 9.0) * n / 512.0
            x, y = (x + np.cos(angle) * step) % n, (y + np.sin(angle) * step) % n
            if abs(x - pts[-1][0]) > n / 2 or abs(y - pts[-1][1]) > n / 2:
                canvas.line(pts, value, width)
                pts = [(x, y)]
            else:
                pts.append((x, y))
        if len(pts) > 1:
            canvas.line(pts, value, width)


def _pebbles(rng, n: int, count: int, rmin: float, rmax: float):
    """Small stones: a lit top and a shadow under it, as two masks."""
    light, dark = _WrapCanvas(n), _WrapCanvas(n)
    for _ in range(max(0, count)):
        x, y = rng.uniform(0.0, n, 2)
        r = rng.uniform(rmin, rmax)
        light.ellipse(x, y, r, r * 0.75, 150)
        dark.ellipse(x + r * 0.2, y + r * 1.05, r * 1.1, r * 0.5, 70)
    return light.mask(), dark.mask()


# --- surfaces ---------------------------------------------------------------------

def _plaster(rng, n: int, s: dict) -> np.ndarray:
    """Lime plaster: uneven wash, trowel grain, a few soft damp marks."""
    k = n / 512.0
    broad = _noise(rng, n, 2, 4) - 0.5
    trowel = _noise(rng, n, 12, 3) - 0.5
    v = 0.925 + 0.10 * s["mottle"] * broad + 0.055 * s["grain"] * trowel
    v += 0.012 * rng.normal(0.0, 1.0, (n, n))
    v -= 0.09 * s["stain"] * _stains(rng, n, 3, 3, radius=5 * k)
    v -= 0.05 * s["mottle"] * _stains(rng, n, 7, 2, radius=2 * k)
    return v


def _render(rng, n: int, s: dict) -> np.ndarray:
    """Cement render: finer and flatter than plaster, with faint float sweeps."""
    k = n / 512.0
    y, x = np.mgrid[0:n, 0:n]
    broad = _noise(rng, n, 2, 3) - 0.5
    sand = _noise(rng, n, 32, 2) - 0.5
    sweep = np.sin(2.0 * np.pi * (2.0 * x + y) / n + 2.0 * _noise(rng, n, 2, 2))
    v = 0.905 + 0.05 * s["mottle"] * broad + 0.035 * s["grain"] * sand
    v += 0.010 * s["grain"] * sweep
    v += 0.010 * rng.normal(0.0, 1.0, (n, n))
    v -= 0.06 * s["stain"] * _stains(rng, n, 4, 3, radius=6 * k)
    return v


def _render_cream(rng, n: int, s: dict) -> np.ndarray:
    """Colonial render with one moulded string course per repeat (bottom = floor line).

    The palette gives this texture `texture_size = [3.0, 3.6]`, the colonial floor height, so
    the band lands on every floor line. Wall UVs put v = 0 at the ground (prompt 19), and glTF
    viewers flip images vertically, so "bottom" is the last image row.
    """
    v = _render(rng, n, s)
    rows = (n - 1 - np.arange(n, dtype=np.float64)) / n      # 0 at the bottom row, 1 at the top
    profile = np.zeros(n)
    profile += 0.09 * np.exp(-((rows - 0.052) / 0.012) ** 2)   # lit top of the moulding
    profile -= 0.13 * np.exp(-((rows - 0.030) / 0.010) ** 2)   # shadow under it
    profile -= 0.05 * np.exp(-((rows - 0.010) / 0.005) ** 2)   # dirt just above the floor line
    return v + s["band"] * profile[:, None]


def _stone(rng, n: int, s: dict) -> np.ndarray:
    """Cut ashlar: three blocks across, four rows, staggered, thin recessed joints."""
    y, x = np.mgrid[0:n, 0:n]
    rows, cols = 4, 3
    u = x * cols / n
    vv = y * rows / n
    row = np.floor(vv).astype(np.int64) % rows
    off = np.where(row % 2 == 0, 0.0, 0.5)
    uu = (u + off) % 1.0
    col = np.floor(u + off).astype(np.int64) % cols
    fv = vv % 1.0
    tone = rng.normal(0.0, 0.060, (rows, cols))[row, col]
    tilt_u = rng.normal(0.0, 0.030, (rows, cols))[row, col]
    tilt_v = rng.normal(0.0, 0.030, (rows, cols))[row, col]
    ju = np.minimum(uu, 1.0 - uu) * (n / cols)       # distance to the joint, in pixels
    jv = np.minimum(fv, 1.0 - fv) * (n / rows)
    joint = (ju < 1.2) | (jv < 1.5)
    face = 0.900 + tone + tilt_u * (uu - 0.5) + tilt_v * (fv - 0.5)
    # each block is slightly bevelled: its top and left edges catch light, the others sink
    face += 0.035 * (1.0 - smoothstep(0.0, 0.08, fv)) - 0.045 * smoothstep(0.92, 1.0, fv)
    face += 0.020 * (1.0 - smoothstep(0.0, 0.06, uu)) - 0.020 * smoothstep(0.94, 1.0, uu)
    face += 0.08 * s["mottle"] * (_noise(rng, n, 2, 4) - 0.5) * 2.0
    face += 0.06 * s["grain"] * (_noise(rng, n, 24, 3) - 0.5) * 2.0
    face += 0.018 * rng.normal(0.0, 1.0, (n, n))
    face -= 0.25 * _blur((rng.random((n, n)) < 0.003).astype(np.float64), 0.8 * n / 512.0)
    mortar = 0.660 + 0.04 * s["grain"] * rng.normal(0.0, 1.0, (n, n))
    v = np.where(joint, mortar, face)
    v -= 0.08 * s["stain"] * _stains(rng, n, 3, 3, radius=5 * n / 512.0)
    return v


def _concrete(rng, n: int, s: dict) -> np.ndarray:
    """Modern concrete: aggregate, vertical formwork seams, tie holes and rain streaks."""
    k = n / 512.0
    y, x = np.mgrid[0:n, 0:n]
    v = 0.890 + 0.06 * s["mottle"] * (_noise(rng, n, 2, 3) - 0.5) * 2.0
    v += 0.045 * s["grain"] * (_noise(rng, n, 64, 2) - 0.5) * 2.0
    v += 0.016 * rng.normal(0.0, 1.0, (n, n))
    seam = (x + 0.5) % (n // 4)
    seam = np.minimum(seam, n // 4 - seam)
    w1, w2 = max(1.4 * k, 1.0), max(1.0 * k, 0.8)
    v -= 0.12 * np.exp(-(seam ** 2) / (2.0 * w1 ** 2))
    v += 0.035 * np.exp(-((seam - 3.0 * k) ** 2) / (2.0 * w2 ** 2))
    for cx in (n // 8, 3 * n // 8, 5 * n // 8, 7 * n // 8):
        for cy in (n // 8, 3 * n // 8, 5 * n // 8, 7 * n // 8):
            r2 = (x - cx) ** 2 + (y - cy) ** 2
            v -= 0.22 * np.exp(-r2 / (2.0 * (2.8 * k) ** 2))
            v += 0.06 * np.exp(-((np.sqrt(r2) - 5.5 * k) ** 2) / (2.0 * (1.4 * k) ** 2))
    streak = np.clip((_line_noise(rng, n, 8, 3) - 0.55) * 3.0, 0.0, 1.0)
    v -= 0.07 * s["stain"] * streak[:, None]
    v -= 0.06 * s["stain"] * _stains(rng, n, 4, 3, radius=6 * k)
    return v


def _roof_tile(rng, n: int, s: dict) -> np.ndarray:
    """Barrel pantiles running down the slope: eight tiles across, four rows of overlaps."""
    k = n / 512.0
    y, x = np.mgrid[0:n, 0:n]
    cols, rows = 8, 4
    fu = (x * cols / n + 0.5) % 1.0
    fv = (y * rows / n + 0.5) % 1.0                 # tile edges sit inside the image, not on it
    col = np.floor(x * cols / n + 0.5).astype(np.int64) % cols
    row = np.floor(y * rows / n + 0.5).astype(np.int64) % rows
    # alternate rows sit a hair to the left or right: hand-laid tiles never form a perfect sheet
    fu = (fu + np.where(row % 2 == 0, -0.030, 0.030)) % 1.0
    barrel = np.sin(np.pi * fu) ** 0.55
    tone = rng.normal(0.0, 0.060, (rows, cols))[row, col]
    butt = smoothstep(0.0, 0.22, fv)
    v = (0.800 + 0.155 * barrel + tone) * (0.78 + 0.22 * butt)
    v += 0.065 * np.exp(-((fv - 0.03) / 0.030) ** 2)          # worn, lighter lower lip
    # the side lap of each tile: a thin shadow at the valley
    lap = np.exp(-(np.minimum(fu, 1.0 - fu) / 0.014) ** 2)
    v -= 0.11 * lap * (0.55 + 0.45 * smoothstep(0.0, 0.25, fv))
    chips = _WrapCanvas(n)
    for _ in range(max(2, int(34 * k * k))):
        chips.ellipse(rng.uniform(0.0, n), rng.uniform(0.0, n),
                      rng.uniform(1.0, 2.6) * k, rng.uniform(0.8, 2.0) * k, 160)
    v -= 0.07 * chips.mask()
    v += 0.04 * s["mottle"] * (_noise(rng, n, 2, 4) - 0.5) * 2.0
    v += 0.022 * s["grain"] * rng.normal(0.0, 1.0, (n, n))
    v -= 0.12 * s["stain"] * _stains(rng, n, 4, 3, radius=4 * k)
    return v


def _roof_flat(rng, n: int, s: dict) -> np.ndarray:
    """Flat-roof screed: chalky, patched, with hairline cracks and small stones."""
    k = n / 512.0
    v = 0.845 + 0.12 * s["mottle"] * (_noise(rng, n, 2, 4) - 0.5) * 2.0
    v += 0.06 * s["grain"] * (_noise(rng, n, 18, 3) - 0.5) * 2.0
    v += 0.016 * rng.normal(0.0, 1.0, (n, n))
    cracks = _WrapCanvas(n)
    _cracks(cracks, rng, n, count=max(3, int(14 * k)), steps=(5, 16), value=110, width=2)
    v -= 0.14 * cracks.mask()
    light, dark = _pebbles(rng, n, count=int(45 * k), rmin=0.8 * k, rmax=1.8 * k)
    v += 0.09 * light - 0.08 * dark
    v -= 0.13 * s["stain"] * _stains(rng, n, 3, 3, radius=6 * k)
    v += 0.05 * _stains(rng, n, 6, 2, radius=3 * k)          # pale lime repairs
    return v


def _paving(rng, n: int, s: dict) -> np.ndarray:
    """Stone paving slabs, four across and four rows, running bond, bevelled and worn."""
    k = n / 512.0
    y, x = np.mgrid[0:n, 0:n]
    rows = cols = 4
    u = x * cols / n
    vv = y * rows / n
    row = np.floor(vv).astype(np.int64) % rows
    off = np.where(row % 2 == 0, 0.0, 0.5)
    uu = (u + off) % 1.0
    col = np.floor(u + off).astype(np.int64) % cols
    fv = vv % 1.0
    tone = rng.normal(0.0, 0.060, (rows, cols))[row, col]
    tilt_u = rng.normal(0.0, 0.020, (rows, cols))[row, col]
    tilt_v = rng.normal(0.0, 0.020, (rows, cols))[row, col]
    ju = np.minimum(uu, 1.0 - uu) * (n / cols)
    jv = np.minimum(fv, 1.0 - fv) * (n / rows)
    joint = (ju < 1.2) | (jv < 1.5)
    face = 0.900 + tone + tilt_u * (uu - 0.5) + tilt_v * (fv - 0.5)
    face += 0.06 * s["mottle"] * (_noise(rng, n, 2, 4) - 0.5) * 2.0
    face += 0.035 * s["grain"] * (_noise(rng, n, 40, 2) - 0.5) * 2.0
    face += 0.016 * rng.normal(0.0, 1.0, (n, n))
    face += 0.035 * (1.0 - smoothstep(0.0, 0.06, fv)) - 0.045 * smoothstep(0.94, 1.0, fv)
    face += 0.020 * (1.0 - smoothstep(0.0, 0.05, uu)) - 0.020 * smoothstep(0.95, 1.0, uu)
    mortar = 0.680 + 0.02 * rng.normal(0.0, 1.0, (n, n))
    v = np.where(joint, mortar, face)
    v -= 0.10 * s["stain"] * _stains(rng, n, 3, 3, radius=6 * k)
    v -= 0.14 * _blur((rng.random((n, n)) < 0.003).astype(np.float64), 1.0 * k)
    return v


def _asphalt(rng, n: int, s: dict) -> np.ndarray:
    """Sun-bleached asphalt: coarse aggregate, patches and a few fine cracks."""
    k = n / 512.0
    chance = rng.random((n, n))
    chips = _blur((chance > 0.930).astype(np.float64), 1.1 * k)
    pits = _blur((chance < 0.070).astype(np.float64), 1.2 * k)
    v = 0.850 + 0.18 * chips - 0.11 * pits
    v += 0.04 * s["grain"] * rng.normal(0.0, 1.0, (n, n))
    v += 0.08 * s["mottle"] * (_noise(rng, n, 3, 4) - 0.5) * 2.0
    v -= 0.11 * s["stain"] * _stains(rng, n, 3, 3, radius=8 * k)
    cracks = _WrapCanvas(n)
    _cracks(cracks, rng, n, count=max(2, int(7 * k)), steps=(8, 20), value=105, width=2)
    v -= 0.07 * cracks.mask()
    return v


def _earth(rng, n: int, s: dict) -> np.ndarray:
    """Packed earth: clods, small stones, scuffed patches and damp shadows."""
    k = n / 512.0
    v = 0.870 + 0.10 * s["mottle"] * (_noise(rng, n, 2, 4) - 0.5) * 2.0
    v += 0.05 * s["grain"] * (_noise(rng, n, 8, 4) - 0.5) * 2.0
    v += 0.014 * rng.normal(0.0, 1.0, (n, n))
    light, dark = _pebbles(rng, n, count=int(140 * k * k), rmin=1.1 * k, rmax=2.8 * k)
    v += 0.09 * light - 0.08 * dark
    scuffs = _WrapCanvas(n)
    for _ in range(int(26 * k * k)):
        x, y = rng.uniform(0.0, n, 2)
        angle = rng.uniform(0.0, 2.0 * np.pi)
        length = rng.uniform(8.0, 22.0) * k
        scuffs.line([(x, y), (x + np.cos(angle) * length * 0.6, y + np.sin(angle) * length * 0.6),
                     (x + np.cos(angle + 0.2) * length, y + np.sin(angle + 0.2) * length)], 120)
    v += 0.045 * scuffs.mask()
    v -= 0.07 * s["stain"] * _stains(rng, n, 4, 3, radius=6 * k)
    return v


def _sand(rng, n: int, s: dict) -> np.ndarray:
    """Fine sand: warped wind ripples, mineral grains and a few dark specks."""
    k = n / 512.0
    y, x = np.mgrid[0:n, 0:n]
    warp = (_noise(rng, n, 3, 3) - 0.5) * 2.0
    ripple = np.sin(2.0 * np.pi * (3.0 * x + y) / n + 2.2 * warp)
    ripple = np.sign(ripple) * np.abs(ripple) ** 0.6
    v = 0.920 + 0.11 * s["mottle"] * ripple
    v += 0.020 * s["grain"] * rng.normal(0.0, 1.0, (n, n))
    v -= 0.10 * _blur((rng.random((n, n)) < 0.004).astype(np.float64), 0.5 * k)
    v -= 0.05 * s["stain"] * _stains(rng, n, 4, 2, radius=5 * k)
    return v


def _grass(rng, n: int, s: dict) -> np.ndarray:
    """Dry Mediterranean grass: tufts of blades with worn, pale patches between them."""
    k = n / 512.0
    clump = smoothstep(0.25, 0.65, _noise(rng, n, 4, 4))
    dark, light = _WrapCanvas(n), _WrapCanvas(n)
    for _ in range(int(3000 * k * k)):
        x0, y0 = rng.uniform(0.0, n, 2)
        density = clump[int(y0) % n, int(x0) % n]
        if rng.random() > 0.35 + 0.65 * density:
            continue
        leaning = rng.uniform(0.0, 2.0 * np.pi)      # a tuft leans the same way
        for _ in range(int(rng.integers(5, 12))):
            angle = leaning + rng.normal(0.0, 0.55)
            length = rng.uniform(6.0, 20.0) * k * (0.65 + 0.7 * density)
            x = x0 + rng.normal(0.0, 2.0 * k)
            y = y0 + rng.normal(0.0, 2.0 * k)
            tip = (x + np.cos(angle + rng.normal(0.0, 0.2)) * length,
                   y + np.sin(angle + rng.normal(0.0, 0.2)) * length)
            mid = (x + np.cos(angle) * length * 0.5, y + np.sin(angle) * length * 0.5)
            target = dark if rng.random() < 0.64 else light
            target.line([(x, y), mid, tip], int(rng.uniform(70, 220)),
                        width=2 if rng.random() < 0.35 else 1)
    v = 0.880 + 0.10 * s["mottle"] * (clump - 0.45) * 2.0
    v -= 0.17 * dark.mask()
    v += 0.08 * light.mask()
    v -= 0.06 * _blur(dark.mask(), 2.0 * k)          # shadow between the blades of a tuft
    v += 0.07 * _stains(rng, n, 3, 3, radius=7 * k)  # dry, bare patches
    v += 0.014 * rng.normal(0.0, 1.0, (n, n))
    v -= 0.05 * s["stain"] * _stains(rng, n, 4, 2, radius=4 * k)
    return v


def _rock(rng, n: int, s: dict) -> np.ndarray:
    """Limestone: irregular wavy strata, rough faces, thin joints, pits and weathering."""
    k = n / 512.0
    y, x = np.mgrid[0:n, 0:n]
    count = max(3, int(8 * k))
    thick = rng.uniform(0.6, 1.7, count)
    bounds = np.cumsum(thick / thick.sum() * n)
    warp = ((_noise(rng, n, 3, 3) - 0.5) * 44.0 * k)
    faults = np.sort(rng.uniform(0.0, n, max(2, int(4 * k))))
    throw = rng.normal(0.0, 14.0 * k, len(faults))
    shift = np.zeros((n, n))
    for fx, t in zip(faults, throw):
        shift += t * (x > fx)                    # the beds step up or down across a fault
    yw = (y + warp + shift) % n
    band = np.clip(np.searchsorted(bounds, yw), 0, count - 1)
    tone = rng.normal(0.0, 0.030, count)[band]
    below = np.where(band > 0, bounds[np.maximum(band - 1, 0)], bounds[-1] - n)
    above = np.where(band < count, bounds[np.minimum(band, count - 1)], bounds[0] + n)
    dist = np.minimum(np.abs(yw - below), np.abs(above - yw))
    seam = np.exp(-(dist / (1.4 * k)) ** 2)
    v = 0.800 + tone
    v += 0.13 * s["mottle"] * (_noise(rng, n, 3, 5) - 0.5) * 2.0
    v += 0.06 * s["mottle"] * (_noise(rng, n, 6, 3) - 0.5) * 2.0
    v += 0.08 * s["grain"] * (_noise(rng, n, 10, 4) - 0.5) * 2.0
    v += 0.035 * s["grain"] * (_noise(rng, n, 40, 2) - 0.5) * 2.0
    v -= 0.16 * seam
    faults_canvas = _WrapCanvas(n)
    for fx in faults:
        ys = np.arange(0.0, n + 1.0, 4.0 * k)
        phase = rng.uniform(0.0, 2.0 * np.pi)
        xs = fx + 1.6 * k * np.sin(2.0 * np.pi * 2.0 * ys / n + phase)
        faults_canvas.line(list(zip(xs, ys)), 80, width=int(rng.integers(1, 3)))
    v -= 0.14 * faults_canvas.mask()
    joints = _WrapCanvas(n)
    for _ in range(max(2, int(5 * k))):
        x0 = rng.uniform(0.0, n)
        wave = rng.integers(1, 3)
        phase = rng.uniform(0.0, 2.0 * np.pi)
        ys = np.arange(0.0, n + 1.0, 5.0 * k)
        xs = x0 + rng.uniform(4.0, 10.0) * k * np.sin(2.0 * np.pi * wave * ys / n + phase)
        joints.line(list(zip(xs, ys)), int(rng.uniform(70, 120)), width=int(rng.integers(2, 4)))
    _cracks(joints, rng, n, count=max(2, int(5 * k)), steps=(5, 12), value=100, width=2)
    v -= 0.16 * joints.mask()
    v -= 0.16 * _blur((rng.random((n, n)) < 0.003).astype(np.float64), 0.9 * k)
    v += 0.018 * rng.normal(0.0, 1.0, (n, n))
    v += 0.06 * s["stain"] * _stains(rng, n, 5, 3, radius=5 * k)
    v -= 0.06 * s["stain"] * _stains(rng, n, 3, 3, radius=9 * k)
    return v


def _scrub(rng, n: int, s: dict) -> np.ndarray:
    """Dry scrub floor: packed earth under leaf litter, twigs and small stones."""
    k = n / 512.0
    v = _earth(rng, n, s)
    dark, light = _WrapCanvas(n), _WrapCanvas(n)
    for _ in range(int(2400 * k * k)):
        x, y = rng.uniform(0.0, n, 2)
        angle = rng.uniform(0.0, 2.0 * np.pi)
        length = rng.uniform(2.5, 6.0) * k
        if rng.random() < 0.55:                 # small dry leaves
            target = dark if rng.random() < 0.70 else light
            target.ellipse(x, y, length * 0.9, length * 0.5, int(rng.uniform(80, 190)))
        else:                                   # twigs
            target = dark if rng.random() < 0.55 else light
            target.line([(x, y), (x + np.cos(angle) * length * 1.6,
                                  y + np.sin(angle) * length * 1.6)],
                        int(rng.uniform(90, 200)))
    v -= 0.15 * dark.mask()
    v += 0.07 * light.mask()
    v -= 0.04 * _blur(dark.mask(), 1.4 * k)
    v -= 0.05 * s["stain"] * _stains(rng, n, 4, 3, radius=5 * k)
    return v


def _ballast(rng, n: int, s: dict) -> np.ndarray:
    """A railway sleeper bed seen from above (prompt 33): x runs along the track, y across it, one track per
    repeat with its middle on the first row. Four timber sleepers (2.6 m of the 4 m across, 0.25 m wide,
    grain and worn ends) lie on coarse grey ballast, darker where it is oiled between the rails."""
    k = n / 256.0
    v = 0.80 + 0.08 * s["mottle"] * (_noise(rng, n, 4, 3) - 0.5) * 2.0
    v += 0.10 * s["grain"] * (_noise(rng, n, 32, 2) - 0.5) * 2.0
    v += 0.05 * rng.normal(0.0, 1.0, (n, n))
    light, dark = _pebbles(rng, n, count=int(900 * k * k), rmin=0.9 * k, rmax=2.2 * k)
    v += 0.12 * light - 0.12 * dark
    y, x = np.mgrid[0:n, 0:n]
    across = np.abs(((y + n / 2) % n) - n / 2) / n          # 0 on the track's middle, 0.5 at the bed's edges
    v -= 0.10 * smoothstep(0.24, 0.12, across)               # oil and dust between the rails
    v -= 0.06 * smoothstep(0.40, 0.5, across)                # the bed's shoulders sink into the ground
    wood = 0.52 + 0.06 * (_line_noise(rng, n, 16, 3) - 0.5) * 2.0 + 0.03 * rng.normal(0.0, 1.0, (n, n))
    half = 0.25 / 2.6 * n / 2
    for i in range(4):
        cx = (i + 0.5) * n / 4 + rng.uniform(-0.6, 0.6) * k
        end = 1.3 / 4.0 + rng.uniform(-0.006, 0.006)
        mask = (np.abs(x - cx) <= half) & (across <= end)
        edge = (np.abs(np.abs(x - cx) - half) < 1.0) | (np.abs(across - end) < 1.0 / n)
        v = np.where(mask, wood - 0.08 * edge, v)
        v = np.where((np.abs(x - cx - half - 1.0) < 1.0) & (across <= end), v - 0.10, v)   # its shadow
    return v


_MAKERS = {
    "plaster": _plaster, "render": _render, "render_cream": _render_cream,
    "stone": _stone, "concrete": _concrete,
    "roof_tile": _roof_tile, "roof_flat": _roof_flat,
    "paving": _paving, "asphalt": _asphalt, "earth": _earth, "sand": _sand,
    "grass": _grass, "rock": _rock, "scrub": _scrub, "ballast": _ballast,
}


# --- provider ---------------------------------------------------------------------

def texture(name: str, seed: int, spec: dict | None = None) -> Image.Image:
    """The image for texture `name`: the same pixels for the same seed and name.

    `spec` is a `[textures]` entry from the style (pixels, grain, mottle, stain, band); the
    built-in defaults fill whatever it leaves out.
    """
    if name not in _MAKERS:
        raise ValueError(f"unknown texture {name!r}; known: {', '.join(NAMES)}")
    values = {**DEFAULTS, **(spec or {})}
    size = int(values["pixels"])
    rng = stream(seed, "texture", name)
    value = np.clip(_MAKERS[name](rng, size, values), 0.0, 1.0)
    rgb = np.repeat((value * 255.0 + 0.5).astype(np.uint8)[:, :, None], 3, axis=2)
    return Image.fromarray(rgb, "RGB")


def png_bytes(image: Image.Image) -> bytes:
    """PNG file content, exactly the same bytes for the same pixels."""
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def encode(image: Image.Image, quality: int = 90) -> Encoded:
    """The smaller of PNG and JPEG, so a build packs its shared textures in under 2 MB."""
    png = png_bytes(image)
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality, optimize=True)
    jpg = buf.getvalue()
    if len(jpg) < len(png):
        return Encoded(jpg, "image/jpeg", "jpg")
    return Encoded(png, "image/png", "png")


@lru_cache(maxsize=64)
def _encoded(name: str, seed: int, spec_items: tuple) -> Encoded:
    return encode(texture(name, seed, dict(spec_items)))


def encoded(name: str, seed: int, spec: dict | None = None) -> Encoded:
    """File bytes, MIME type and extension for one texture; cached per process and settings."""
    return _encoded(name, seed, tuple(sorted((spec or {}).items())))


def spec_for(style: dict, name: str) -> dict:
    """The style's `[textures]` entry for `name`, filled with the defaults."""
    return {**DEFAULTS, **style.get("textures", {}).get(name, {})}


def texture_names(style: dict) -> list[str]:
    """Every texture the style declares, in catalogue order (all of them when it declares none)."""
    declared = style.get("textures", {})
    if not declared:
        return list(NAMES)
    return [n for n in NAMES if n in declared] + sorted(n for n in declared if n not in NAMES)


def image_names(style: dict) -> list[str]:
    """Every texture name the palette asks for, sorted."""
    return sorted({spec["texture"] for spec in style.get("palette", {}).values() if spec.get("texture")})


def write_shared_textures(style: dict, seed: int, folder) -> list[str]:
    """Write each image once into `folder/textures/` before any tile; returns the file names.

    Tiles reference them with a relative URI, so parallel workers never write the same image.
    """
    out = Path(folder) / "textures"
    names = image_names(style)
    if names:
        out.mkdir(parents=True, exist_ok=True)
    written = []
    for name in names:
        enc = encoded(name, seed, spec_for(style, name))
        file = f"{name}.{enc.ext}"
        (out / file).write_bytes(enc.data)
        written.append(file)
    return written


def images_for(style: dict, seed: int, mode: str) -> dict:
    """The writer's image table: {texture name: {"uri": path} or {"bytes": data, "mime": type}}.

    "shared": one file per image under the tiles folder, written by the parent process.
    "embedded": the bytes go inside every .glb (single-file exports such as hero scenes).
    "off": no texture at all, flat palette colors.
    """
    names = image_names(style)
    if mode == "shared":
        return {name: {"uri": f"textures/{name}.{encoded(name, seed, spec_for(style, name)).ext}"}
                for name in names}
    if mode == "embedded":
        out = {}
        for name in names:
            enc = encoded(name, seed, spec_for(style, name))
            out[name] = {"bytes": enc.data, "mime": enc.mime}
        return out
    return {}
