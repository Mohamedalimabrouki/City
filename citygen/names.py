"""Invented place names, built from the sounds and patterns listed in the style pack."""
from __future__ import annotations

import re

import numpy as np

# hard to read or foreign-looking: a doubled letter (oo, kk), spellings North African names do not
# use (sh, ts, q), or three consonant sounds in a row once ch, dj, gh, kh and ou count as one
_FOREIGN = re.compile(r"([a-z])\1|sh|ts|q")
_CLUSTER = re.compile(r"[^aeiouyU ]{3,}")
_DIGRAPHS = (("ch", "C"), ("dj", "J"), ("gh", "G"), ("kh", "K"), ("ou", "U"))
# Arabic "sun letters" as spelled in North African French: el + Souk -> es Souk, el + Chott -> ech Chott
_SUN = ("ch", "t", "d", "r", "z", "s", "n", "l")


def _clumsy(name: str) -> bool:
    low = name.lower()
    if _FOREIGN.search(low):
        return True
    for pair, one in _DIGRAPHS:
        low = low.replace(pair, one)
    return bool(_CLUSTER.search(low))


def article(word: str) -> str:
    """The Arabic article joined the North African way: el Kef, but es Souk, ech Chott, er Rmel."""
    w = word.lower()
    if w.startswith("dj"):
        return "el"
    for letter in _SUN:
        if w.startswith(letter):
            return "e" + letter
    return "el"


class NameMaker:
    def __init__(self, style: dict, rng: np.random.Generator):
        self.n = style["names"]
        self.rng = rng
        self.used: set[str] = set()
        self.avoid = {a.lower() for a in self.n.get("avoid", [])}

    def _pick(self, seq):
        return seq[int(self.rng.integers(len(seq)))]

    def _syllable(self, coda_chance: float = 0.45) -> str:
        n = self.n
        coda = self._pick(n["codas"]) if self.rng.random() < coda_chance else ""
        return self._pick(n["onsets"]) + self._pick(n["vowels"]) + coda

    def _core(self) -> str:
        n = self.n
        if self.rng.random() < float(n.get("berber_chance", 0.0)):
            return ("ta" + self._syllable(0.6) + self._pick(n["berber_endings"])).capitalize()
        syllables = 2 if self.rng.random() < 0.6 else 3
        parts = [self._syllable() for _ in range(syllables - 1)]
        parts.append(self._pick(n["onsets"]) + self._pick(n["endings"]))
        return "".join(parts).capitalize()

    def core(self) -> str:
        """A fresh name nobody else in this world uses yet, and no real town has."""
        for _ in range(200):
            name = self._core()
            low = name.lower()
            if name not in self.used and 4 <= len(name) <= 11 and not _clumsy(name) and low not in self.avoid:
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
        n = self.n
        core = self.core()
        roll = self.rng.random()
        prefix_chance = float(n.get("prefix_chance", {}).get(kind, 0.0))
        compound_chance = float(n.get("compound_chance", {}).get(kind, 0.0))
        prefixes = n.get("prefixes", {}).get(kind, [])
        if prefixes and roll < prefix_chance:
            prefix = self._pick(prefixes)
            if prefix in n.get("article_prefixes", []) and self.rng.random() < float(n.get("article_chance", 0.0)):
                return f"{prefix} {article(core)} {core}"
            return f"{prefix} {core}"
        if n.get("descriptors") and roll < prefix_chance + compound_chance:
            desc = self._pick(n["descriptors"])
            return f"{core} {article(desc)} {desc}"
        return core

    def district(self, kind: str) -> str:
        templates = self.n.get("districts", {}).get(kind, ["{n}"])
        core = self.core()
        return self._pick(templates).format(n=core, a=article(core))
