"""Terrain and climate of the whole country, as pure functions of position.

Height comes from a tilted landmass (sea on one side, high steppe on the
other), coastal hills, a mountain range, small islands and fine detail.
Moisture falls off with distance from the sea, so the coast is green and the
far interior is desert.
"""
from __future__ import annotations

import math

import numpy as np

from .noise import Fractal, smoothstep
from .rng import stream

# biome codes
SEA, BEACH, GREEN, STEPPE, DESERT, FOREST, ROCK = range(7)
BIOME_NAMES = ["sea", "beach", "green", "steppe", "desert", "forest", "rock"]
BIOME_MATERIAL = ["water", "beach", "grass", "steppe", "desert", "forest", "rock"]


class Terrain:
    def __init__(self, seed: int, cfg: dict):
        t = cfg["terrain"]
        self.size = float(cfg["world"]["size_km"]) * 1000.0
        rng = stream(seed, "terrain")
        if str(t["sea_direction"]) == "random":
            bearing = rng.uniform(0.0, 360.0)
        else:
            bearing = float(t["sea_direction"])
        a = math.radians(90.0 - bearing)  # compass bearing -> math angle
        self.sea_dir = (math.cos(a), math.sin(a))
        self.coast_position = float(t["coast_position"])
        self.inland_rise = float(t["inland_rise"])
        self.hill_height = float(t["hill_height"])
        self.mountain_height = float(t["mountain_height"])
        self.mountain_band = float(t["mountain_band"])
        self.islands = bool(t["islands"])
        size = self.size
        self.coast_big = Fractal(seed, "coast-big", size * 0.45, octaves=3)
        self.coast_small = Fractal(seed, "coast-small", 7000.0, octaves=3)
        self.hills = Fractal(seed, "hills", 5200.0, octaves=4)
        self.ridges = Fractal(seed, "ridges", 15000.0, octaves=5, gain=0.48)
        self.massif = Fractal(seed, "massif", 30000.0, octaves=2)
        self.island_noise = Fractal(seed, "islands", 5500.0, octaves=3)
        self.detail = Fractal(seed, "detail", 650.0, octaves=3)
        self.wetness = Fractal(seed, "wetness", 11000.0, octaves=3)

    def inland(self, x, y):
        """Signed distance from the coastline in country widths: > 0 inland, < 0 at sea (roughly)."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        s = (x / self.size - 0.5) * self.sea_dir[0] + (y / self.size - 0.5) * self.sea_dir[1]
        warp = 0.2 * self.coast_big(x, y) + 0.06 * self.coast_small(x, y)
        return self.coast_position - s + warp

    def height(self, x, y):
        """Ground height in meters (sea level = 0) at any point(s)."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        t = self.inland(x, y)
        h = np.where(t > 0, t * self.inland_rise, t * 520.0)
        plain = smoothstep(0.0, 0.10, t)
        h = h + self.hill_height * self.hills(x, y) * plain
        band = np.exp(-((t - self.mountain_band) / 0.17) ** 2)
        band = band * (0.35 + 0.65 * smoothstep(-0.35, 0.45, self.massif(x, y)))
        h = h + self.mountain_height * band * self.ridges.ridged(x, y) ** 2
        h = h + 3.0 * self.detail(x, y) * plain
        if self.islands:
            bump = np.clip(self.island_noise(x, y) - 0.42, 0.0, None) * 420.0
            h = h + bump * smoothstep(-0.015, -0.11, t)
        return h

    def moisture(self, x, y, h=None):
        """0 = desert dry, 1 = lush."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        h = self.height(x, y) if h is None else h
        t = np.clip(self.inland(x, y), 0.0, 1.0)
        m = 0.82 - 1.25 * t + 0.22 * self.wetness(x, y) + 0.00045 * np.clip(h - 250.0, 0.0, None)
        return np.clip(m, 0.0, 1.0)

    def slope(self, x, y, d: float = 10.0):
        """Ground slope as rise over run (0.1 = 10 percent)."""
        dx = (self.height(x + d, y) - self.height(x - d, y)) / (2 * d)
        dy = (self.height(x, y + d) - self.height(x, y - d)) / (2 * d)
        return np.hypot(dx, dy)


def classify(h, slope, moisture):
    """Biome code per point from height, slope and moisture arrays."""
    h = np.asarray(h)
    b = np.full(h.shape, STEPPE, dtype=np.int8)
    b[moisture > 0.52] = GREEN
    b[(moisture > 0.5) & (h > 380)] = FOREST
    b[moisture < 0.13] = DESERT
    b[(slope > 0.32) | (h > 950)] = ROCK
    b[(h > 0) & (h < 2.2) & (slope < 0.08)] = BEACH
    b[h <= 0] = SEA
    return b
