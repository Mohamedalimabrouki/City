"""Invented place names, built from the sounds listed in the style pack."""
from __future__ import annotations

import re

import numpy as np

# hard to read: a doubled consonant, or four consonants in a row
_CLUMSY = re.compile(r"([bcdfghjklmnpqrstvwxz])\1|[^aeiouy ]{4,}")


class NameMaker:
    def __init__(self, style: dict, rng: np.random.Generator):
        self.n = style["names"]
        self.rng = rng
        self.used: set[str] = set()

    def _pick(self, seq):
        return seq[int(self.rng.integers(len(seq)))]

    def _core(self) -> str:
        n = self.n
        syllables = 2 if self.rng.random() < 0.6 else 3
        parts = []
        for _ in range(syllables - 1):
            coda = self._pick(n["codas"]) if self.rng.random() < 0.45 else ""
            parts.append(self._pick(n["onsets"]) + self._pick(n["vowels"]) + coda)
        parts.append(self._pick(n["onsets"]) + self._pick(n["endings"]))
        return "".join(parts).capitalize()

    def core(self) -> str:
        """A fresh name nobody else in this world uses yet."""
        for _ in range(200):
            name = self._core()
            if name not in self.used and 4 <= len(name) <= 11 and not _CLUMSY.search(name.lower()):
                self.used.add(name)
                return name
        name = self._core() + self._pick(self.n["endings"])
        self.used.add(name)
        return name

    def country(self) -> str:
        core = self.core()
        stem = core[:-1] if core[-1] in "aeiou" else core
        return stem + self._pick(self.n["country_endings"])

    def settlement(self, kind: str) -> str:
        core = self.core()
        chance = float(self.n.get("prefix_chance", {}).get(kind, 0.0))
        prefixes = self.n.get("prefixes", {}).get(kind, [])
        if prefixes and self.rng.random() < chance:
            return f"{self._pick(prefixes)} {core}"
        return core

    def district(self, kind: str) -> str:
        templates = self.n.get("districts", {}).get(kind, ["{n}"])
        return self._pick(templates).format(n=self.core())
