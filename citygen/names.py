"""Invented place names, built from the sounds and patterns listed in the style pack."""
from __future__ import annotations

import re
import string

import numpy as np

from .rng import weighted

# hard to read or foreign-looking: a doubled letter (oo, kk), spellings North African names do not
# use (sh, ts, q), or three consonant sounds in a row once ch, dj, gh, kh and ou count as one
_FOREIGN = re.compile(r"([a-z])\1|sh|ts|sch|q")
_CLUSTER = re.compile(r"[^aeiouyU ]{3,}")
_DIGRAPHS = (("ch", "C"), ("dj", "J"), ("gh", "G"), ("kh", "K"), ("ou", "U"))
# Arabic "sun letters" as spelled in North African French: el + Souk -> es Souk, el + Chott -> ech Chott
_SUN = ("ch", "t", "d", "r", "z", "s", "n", "l")


# The Arabic article and "Bou" are written joined to the next word: Ras el Mokrane is رأس المقران, Bou Salem بوسالم
_JOINED_AR = re.compile(r"(^|\s)(ال|بو) ")
_ARABIC = re.compile(r"[\u0621-\u063A\u0641-\u064A\u06A4\u06A8]")
# twin lists in [names]: each Arabic list has one entry per entry of its Latin list
TWINS = ("onsets", "vowels", "codas", "endings", "berber_endings", "country_endings", "descriptors")


class Name(str):
    """A Latin name that also carries its Arabic spelling in `.ar` ("" when the style has none)."""

    def __new__(cls, latin: str, ar: str = ""):
        obj = super().__new__(cls, latin)
        obj.ar = ar
        return obj

    def __reduce__(self):
        return Name, (str(self), self.ar)


def is_arabic(text: str) -> bool:
    """True when `text` holds only Arabic letters, spaces and the digits 0-9 (and at least one letter)."""
    return bool(text) and all(c == " " or c.isdigit() and c.isascii() or _ARABIC.match(c) for c in text)


def join_ar(*words: str) -> str:
    """Arabic words with spaces, the article ال and بو joined to the word after them."""
    text = " ".join(w for w in words if w)
    while _JOINED_AR.search(text):
        text = _JOINED_AR.sub(r"\1\2", text)
    return text


def fill_ar(template: str, **fields) -> str:
    """An Arabic template filled with the Arabic of each field (a Name's `.ar`, or a plain string);
    "" when a field it needs has no Arabic spelling."""
    values = {}
    for _, key, _, _ in string.Formatter().parse(template):
        if key is None:
            continue
        v = fields.get(key, "")
        v = v.ar if isinstance(v, Name) else ("" if v is None else str(v))
        if not v or not is_arabic(v):
            return ""
        values[key] = v
    return join_ar(template.format(**values))


def _spell_ar(parts: list) -> str:
    """One word from (Latin, Arabic) parts, read the way the Latin word reads:
    - a dropped short "a" is written ا between two equal letters (it would read as one doubled letter) and
      before a part that starts with a vowel (Takhaount: تخاونت, not تخونت);
    - a coda "k" before an onset "h" reads "kh" in the Latin word, so the two are one خ;
    - a ة or ى inside the word (an ending followed by more) is ا."""
    out = ""
    for k, (lat, ar) in enumerate(parts):
        nxt_lat = next((p for p, _ in parts[k + 1:] if p), "")
        if lat == "a" and not ar and out:
            nxt = next((a for _, a in parts[k + 1:] if a), "")
            if (nxt and nxt[0] == out[-1]) or nxt_lat[:1] in tuple("aeiou"):
                ar = "ا"
        if lat == "h" and out.endswith("ك") and parts[k - 1][0].endswith("k"):
            out, ar = out[:-1], "خ"
        out += ar
    return re.sub(r"[ةى](?=.)", "ا", out)


def _cut_ar(lat: str, ar: str) -> str:
    """The Arabic of a part once its last Latin letter is cut: "ia" ية -> "i" ي, "ane" ان -> "an" ان."""
    if lat.endswith("e"):
        return ar
    if lat.endswith("a"):
        return ar[:-1] if ar[-1:] in ("ة", "ى", "ا") else ar
    if lat.endswith("i") or (lat.endswith("o") and not lat.endswith("ou")):
        return ar[:-1] if ar[-1:] in ("ي", "و") else ar
    return ar


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


def _root_fits(pattern: str, root: list, roots: dict) -> bool:
    """Sound rules for a root in a pattern: no repeats, no clashing neighbours, no hard clusters."""
    if len(set(root)) < 3 or sum(c in roots["heavy"] for c in root) > 1:
        return False
    if set(root) & {c for c in pattern if c.isalpha() and c not in "aeiou"}:   # ma12ou3i: no root m
        return False
    for a, b in ((0, 1), (1, 2)):
        if any(root[a] in group and root[b] in group for group in roots["classes"]):
            return False
    for k in range(len(pattern) - 1):                   # two root sounds side by side in the name
        if pattern[k].isdigit() and pattern[k + 1].isdigit():
            x, y = root[int(pattern[k]) - 1], root[int(pattern[k + 1]) - 1]
            if (k == 0 and y not in roots["opening"]) or y in roots["never_second"]:
                return False
            if x not in roots["soft"] and y not in roots["soft"]:
                return False
    return True


class NameMaker:
    def __init__(self, style: dict, rng: np.random.Generator):
        self.n = style["names"]
        self.rng = rng
        self.used: set[str] = set()
        self.avoid = {a.lower() for a in self.n.get("avoid", [])}
        self.ar = _twins(self.n)

    def _pick(self, seq):
        return seq[int(self.rng.integers(len(seq)))]

    def _pick_i(self, seq) -> tuple:
        """(index, value): the same single draw as `_pick`, so the Arabic twin at that index can follow."""
        i = int(self.rng.integers(len(seq)))
        return i, seq[i]

    def _part(self, key: str) -> tuple:
        """A (Latin, Arabic) part from the list `key` of [names] and its `key_ar` twin."""
        i, lat = self._pick_i(self.n[key])
        return lat, (self.ar[key][i] if self.ar else "")

    def _syllable_parts(self, coda_chance: float = 0.45) -> list:
        # the coda is drawn first but written last, as in the Latin name
        coda = self._part("codas") if self.rng.random() < coda_chance else ("", "")
        onset = self._part("onsets")
        return [onset, self._part("vowels"), coda]

    def _syllable(self, coda_chance: float = 0.45) -> str:
        return "".join(lat for lat, _ in self._syllable_parts(coda_chance))

    def _core_parts(self) -> list:
        n = self.n
        if self.rng.random() < float(n.get("berber_chance", 0.0)):
            return [("ta", "ت"), *self._syllable_parts(0.6), self._part("berber_endings")]
        syllables = 2 if self.rng.random() < 0.6 else 3
        parts = [p for _ in range(syllables - 1) for p in self._syllable_parts()]
        onset = self._part("onsets")
        parts += [onset, self._part("endings")]
        return parts

    def _core(self) -> str:
        return "".join(lat for lat, _ in self._core_parts()).capitalize()

    def core_parts(self) -> list:
        """The parts of a fresh name nobody else in this world uses yet, and no real town has."""
        for _ in range(200):
            parts = self._core_parts()
            name = "".join(lat for lat, _ in parts).capitalize()
            low = name.lower()
            if name not in self.used and 4 <= len(name) <= 11 and not _clumsy(name) and low not in self.avoid:
                self.used.add(name)
                return parts
        parts = self._core_parts() + [self._part("endings")]
        self.used.add("".join(lat for lat, _ in parts).capitalize())
        return parts

    def _name(self, parts: list) -> Name:
        return Name("".join(lat for lat, _ in parts).capitalize(), _spell_ar(parts) if self.ar else "")

    def core(self) -> Name:
        """A fresh name nobody else in this world uses yet, and no real town has."""
        return self._name(self.core_parts())

    def fits(self, name: str) -> bool:
        """True when a generated name passes the same filters as place names."""
        return not _clumsy(name) and name.lower() not in self.avoid

    def root_word(self, roots: dict) -> str:
        """A made-up nisba the Arabic way: three root sounds set in a word pattern (H-M-D in 1a23i = Hamdi)."""
        for _ in range(200):
            pattern = weighted(self.rng, roots["patterns"])
            root = [weighted(self.rng, roots["sounds"]) for _ in range(3)]
            if not _root_fits(pattern, root, roots):
                continue
            name = "".join(root[int(c) - 1] if c.isdigit() else c for c in pattern).capitalize()
            if self.fits(name) and not any(part in name.lower() for part in roots["avoid_parts"]):
                return name
        # never hand back a refused name (it may hold a blocked word): the style's rules are too tight
        raise ValueError("no made-up family name passes the rules in [life] roots.*; check the style")

    def country(self) -> Name:
        parts = self.core_parts()
        lat, ar = parts[-1]
        if lat[-1] in "aeiou":
            parts[-1] = (lat[:-1], _cut_ar(lat, ar) if self.ar else "")
        stem = self._name(parts)
        lat, ar = self._part("country_endings")
        return Name(stem + lat, _spell_ar([(stem, stem.ar), (lat, ar)]) if self.ar else "")

    def settlement(self, kind: str) -> Name:
        n = self.n
        core = self.core()
        roll = self.rng.random()
        prefix_chance = float(n.get("prefix_chance", {}).get(kind, 0.0))
        compound_chance = float(n.get("compound_chance", {}).get(kind, 0.0))
        prefixes = n.get("prefixes", {}).get(kind, [])
        if prefixes and roll < prefix_chance:
            i, prefix = self._pick_i(prefixes)
            pre_ar = self.ar["prefixes"][kind][i] if self.ar else ""
            if prefix in n.get("article_prefixes", []) and self.rng.random() < float(n.get("article_chance", 0.0)):
                return Name(f"{prefix} {article(core)} {core}", join_ar(pre_ar, "ال", core.ar) if self.ar else "")
            return Name(f"{prefix} {core}", join_ar(pre_ar, core.ar) if self.ar else "")
        if n.get("descriptors") and roll < prefix_chance + compound_chance:
            desc, desc_ar = self._part("descriptors")
            return Name(f"{core} {article(desc)} {desc}", join_ar(core.ar, "ال", desc_ar) if self.ar else "")
        return core

    def district(self, kind: str, **extra) -> Name:
        """A name from the `[names.districts]` templates of `kind`; `extra` fills other fields ({s}). An
        extra that is a `Name` fills the Arabic twin template in `[names.districts_ar]` with its `.ar`."""
        templates = self.n.get("districts", {}).get(kind, ["{n}"])
        core = self.core()
        i, template = self._pick_i(templates)
        latin = template.format(n=core, a=article(core), **extra)
        twins = self.n.get("districts_ar", {}).get(kind, ["{n}"] if kind not in self.n.get("districts", {}) else [])
        ar = fill_ar(twins[i], n=core, **extra) if self.ar and i < len(twins) else ""
        return Name(latin, ar)


def fixed_name(style: dict, key: str, **fields) -> Name:
    """A name from one fixed template of [names] (no random draw), with its `key_ar` twin."""
    n = style["names"]
    latin = n[key].format(**fields)
    twin = n.get(key + "_ar")
    return Name(latin, fill_ar(twin, **fields) if twin and _twins(n) else "")


def _twins(n: dict) -> dict:
    """The Arabic twins of the [names] lists, or {} when the style has none (every name then has no Arabic).
    With `g_ar` set, every Latin "g" onset is spelled with it (ڨ, the Tunisian g) instead of ق."""
    if not all(k + "_ar" in n for k in TWINS) or "prefixes_ar" not in n:
        return {}
    out = {k: list(n[k + "_ar"]) for k in TWINS}
    g = n.get("g_ar")
    if g:
        out["onsets"] = [g if lat == "g" else ar for lat, ar in zip(n["onsets"], out["onsets"])]
    out["prefixes"] = n["prefixes_ar"]
    return out
