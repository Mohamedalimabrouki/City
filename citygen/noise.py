"""Smooth 2D noise (Perlin gradient noise and fractal sums), vectorized with numpy.

Noise is a pure function of position, so any piece of the world can be
evaluated on its own: this is what lets tiles be built independently.
"""
from __future__ import annotations

import math

import numpy as np

from .rng import stream

_GRAD = np.array([[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0],
                  [0.7071, 0.7071], [-0.7071, 0.7071], [0.7071, -0.7071], [-0.7071, -0.7071]])
STACKED_MAX = 4096   # queries up to this many points compute all octaves in one pass


class Perlin:
    """Gradient noise with values roughly in [-1, 1] and features about 1 unit wide."""

    def __init__(self, seed: int, *path):
        rng = stream(seed, "noise", *path)
        p = rng.permutation(256)
        self.perm = np.concatenate([p, p]).astype(np.int64)
        self.offset = rng.uniform(0.0, 256.0, size=2)

    def __call__(self, x, y):
        x = np.asarray(x, dtype=np.float64) + self.offset[0]
        y = np.asarray(y, dtype=np.float64) + self.offset[1]
        x0, y0 = np.floor(x), np.floor(y)
        fx, fy = x - x0, y - y0
        xi = x0.astype(np.int64) & 255
        yi = y0.astype(np.int64) & 255
        perm = self.perm

        def corner(h, dx, dy):
            g = _GRAD[h & 7]
            return g[..., 0] * dx + g[..., 1] * dy

        n00 = corner(perm[perm[xi] + yi], fx, fy)
        n10 = corner(perm[perm[xi + 1] + yi], fx - 1.0, fy)
        n01 = corner(perm[perm[xi] + yi + 1], fx, fy - 1.0)
        n11 = corner(perm[perm[xi + 1] + yi + 1], fx - 1.0, fy - 1.0)
        u = fx * fx * fx * (fx * (fx * 6.0 - 15.0) + 10.0)
        v = fy * fy * fy * (fy * (fy * 6.0 - 15.0) + 10.0)
        a = n00 + u * (n10 - n00)
        b = n01 + u * (n11 - n01)
        return (a + v * (b - a)) * 1.41


class _Octaves:
    """The tables of several Perlin layers side by side, so small queries evaluate them all in one pass.

    Layer k is sampled at ((x c_k - y s_k) f_k, (x s_k + y c_k) f_k), exactly as `Fractal` feeds each
    Perlin layer, then with the same elementwise operations as `Perlin.__call__`: the values are
    bit-identical, only numpy's per-call overhead is saved.
    """

    def __init__(self, layers: list, rot: list, freqs: list):
        self.cos = np.array([c for c, _ in rot], dtype=np.float64)
        self.sin = np.array([s for _, s in rot], dtype=np.float64)
        self.freqs = np.array(freqs, dtype=np.float64)
        self.offsets = np.array([layer.offset for layer in layers], dtype=np.float64).reshape(-1, 2)
        self.base = np.arange(len(layers), dtype=np.int64) * 512
        self.perms = np.concatenate([layer.perm for layer in layers]) if layers else np.zeros(0, np.int64)

    @staticmethod
    def join(parts: list) -> "_Octaves":
        out = _Octaves([], [], [])
        out.cos, out.sin, out.freqs = (np.concatenate([getattr(p, a) for p in parts]) for a in ("cos", "sin", "freqs"))
        out.offsets = np.concatenate([p.offsets for p in parts])
        out.perms = np.concatenate([p.perms for p in parts])
        out.base = np.arange(len(out.cos), dtype=np.int64) * 512
        return out

    def __call__(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Every layer's noise, shape (layers,) + x.shape."""
        col = (-1,) + (1,) * x.ndim
        c, s, freq = self.cos.reshape(col), self.sin.reshape(col), self.freqs.reshape(col)
        px = (x * c - y * s) * freq + self.offsets[:, 0].reshape(col)
        py = (x * s + y * c) * freq + self.offsets[:, 1].reshape(col)
        x0, y0 = np.floor(px), np.floor(py)
        fx, fy = px - x0, py - y0
        xi = x0.astype(np.int64) & 255
        yi = y0.astype(np.int64) & 255
        perm, base = self.perms, self.base.reshape(col)
        gx, gy = _GRAD[:, 0], _GRAD[:, 1]

        def corner(h, dx, dy):
            h = h & 7
            return gx[h] * dx + gy[h] * dy

        px0, px1 = perm[base + xi] + base, perm[base + xi + 1] + base
        n00 = corner(perm[px0 + yi], fx, fy)
        n10 = corner(perm[px1 + yi], fx - 1.0, fy)
        n01 = corner(perm[px0 + yi + 1], fx, fy - 1.0)
        n11 = corner(perm[px1 + yi + 1], fx - 1.0, fy - 1.0)
        u = fx * fx * fx * (fx * (fx * 6.0 - 15.0) + 10.0)
        v = fy * fy * fy * (fy * (fy * 6.0 - 15.0) + 10.0)
        a = n00 + u * (n10 - n00)
        b = n01 + u * (n11 - n01)
        return (a + v * (b - a)) * 1.41


def stackable(x: np.ndarray, y: np.ndarray) -> bool:
    """Small queries (up to STACKED_MAX points) evaluate all octaves in one pass."""
    return x.shape == y.shape and x.size <= STACKED_MAX


class Fractal:
    """Sum of noise octaves. `wavelength` is the size of the largest features, in meters."""

    def __init__(self, seed: int, name: str, wavelength: float, octaves: int = 4,
                 gain: float = 0.5, lacunarity: float = 2.0):
        self.layers = [Perlin(seed, name, o) for o in range(octaves)]
        self.freq = 1.0 / wavelength
        self.gain = gain
        self.lacunarity = lacunarity
        # rotate each octave so grid-aligned artefacts do not stack up
        self.rot = [(math.cos(o * 2.39996), math.sin(o * 2.39996)) for o in range(octaves)]
        freqs, self.amps, freq, amp = [], [], self.freq, 1.0
        for _ in range(octaves):
            freqs.append(freq)
            self.amps.append(amp)
            freq *= lacunarity
            amp *= gain
        self.octaves = _Octaves(self.layers, self.rot, freqs)

    def _octaves(self, x, y):
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        if stackable(x, y):
            yield from zip(self.amps, self.octaves(x, y))
            return
        freq, amp = self.freq, 1.0
        for layer, (c, s) in zip(self.layers, self.rot):
            yield amp, layer((x * c - y * s) * freq, (x * s + y * c) * freq)
            freq *= self.lacunarity
            amp *= self.gain

    def __call__(self, x, y):
        """Values roughly in [-1, 1], centered on 0."""
        return self.total(self._octaves(x, y))

    def ridged(self, x, y):
        """Sharp ridges (mountain crests), values in [0, 1]."""
        return self.ridged_total(self._octaves(x, y))

    @staticmethod
    def total(octaves):
        """`__call__` from (amplitude, noise) pairs."""
        total = norm = 0.0
        for amp, n in octaves:
            total = total + amp * n
            norm += amp
        return total / norm

    @staticmethod
    def ridged_total(octaves):
        """`ridged` from (amplitude, noise) pairs."""
        total = norm = 0.0
        for amp, n in octaves:
            total = total + amp * (1.0 - np.abs(n)) ** 2
            norm += amp
        return total / norm


class FractalSet:
    """Several fractals evaluated in one pass on small queries: `pairs(x, y)` gives each fractal's
    (amplitude, noise) pairs, to pass to `Fractal.total` or `Fractal.ridged_total`."""

    def __init__(self, fractals: list):
        self.fractals = fractals
        self.octaves = _Octaves.join([f.octaves for f in fractals])
        self.cuts = np.cumsum([len(f.amps) for f in fractals])[:-1].tolist()

    def pairs(self, x: np.ndarray, y: np.ndarray) -> list:
        rows = np.split(self.octaves(x, y), self.cuts) if self.fractals else []
        return [list(zip(f.amps, r)) for f, r in zip(self.fractals, rows)]


def smoothstep(edge0: float, edge1: float, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)
