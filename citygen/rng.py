"""Deterministic random numbers.

Every random choice comes from a stream keyed by the world seed plus a
purpose path, for example stream(seed, "city", 3, "parcels"). Each feature
owns its stream, so adding or changing one feature never reshuffles the
others: a world stays recognisable while the generator grows.
"""
from __future__ import annotations

import hashlib

import numpy as np


def key(*parts) -> int:
    h = hashlib.blake2b(digest_size=16)
    for part in parts:
        h.update(repr(part).encode("utf-8"))
        h.update(b"\x1f")
    return int.from_bytes(h.digest(), "little")


def stream(seed: int, *path) -> np.random.Generator:
    return np.random.default_rng(key(seed, *path))


def weighted(rng: np.random.Generator, pairs):
    """Pick from [[value, weight], ...] or {value: weight}."""
    if isinstance(pairs, dict):
        pairs = list(pairs.items())
    values = [p[0] for p in pairs]
    weights = np.array([float(p[1]) for p in pairs])
    return values[int(rng.choice(len(values), p=weights / weights.sum()))]
