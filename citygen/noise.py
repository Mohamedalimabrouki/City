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

    def _octaves(self, x, y):
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        freq, amp = self.freq, 1.0
        for layer, (c, s) in zip(self.layers, self.rot):
            yield amp, layer((x * c - y * s) * freq, (x * s + y * c) * freq)
            freq *= self.lacunarity
            amp *= self.gain

    def __call__(self, x, y):
        """Values roughly in [-1, 1], centered on 0."""
        total = norm = 0.0
        for amp, n in self._octaves(x, y):
            total = total + amp * n
            norm += amp
        return total / norm

    def ridged(self, x, y):
        """Sharp ridges (mountain crests), values in [0, 1]."""
        total = norm = 0.0
        for amp, n in self._octaves(x, y):
            total = total + amp * (1.0 - np.abs(n)) ** 2
            norm += amp
        return total / norm


def smoothstep(edge0: float, edge1: float, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)
