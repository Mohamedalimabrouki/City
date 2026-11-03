"""District histories (prompt 81): two to four sentences per district, for writing stories.

Built from the style's `[history]` templates and the facts of the plan only: the era the settlement
was founded in (`[lore] eras`, never earlier for a district than for its city), the district's kind,
where it lies from the old town, the landmarks inside it (gates, the kasbah, mosques, the cathedral and
the theatre, the station, a cemetery's shrines), its souks, its households' trades and its quays.
Every choice comes from its own stream ("history", district id), so nothing else moves. A text in the world file's
`[canon.histories."<city>"]` table, keyed by the district's name, replaces the generated one.
"""
from __future__ import annotations

import collections
import math

from shapely.geometry import Point

COMPASS = ["east", "north-east", "north", "north-west", "west", "south-west", "south", "south-east"]


def histories(ctx, plan) -> None:
    """Set `history` on every district of the plan."""
    style = ctx.style.get("history", {})
    if not style:
        return
    canon = ctx.world.cfg.get("canon", {}).get("histories", {}).get(ctx.s.name, {})
    facts = _Facts(ctx, plan, style)
    for d in plan.districts:
        if d.name in canon:
            d.history = str(canon[d.name])
            continue
        d.history = _history(ctx, style, facts, d)


class _Facts:
    """What the map says about each district."""

    def __init__(self, ctx, plan, style):
        self.plan = plan
        self.eras = [str(e) for e in ctx.style.get("lore", {}).get("eras", [])]
        self.founded = self.eras.index(ctx.s.founded) if ctx.s.founded in self.eras else 0
        self.medina = next((d for d in plan.districts if d.kind == "medina"), None)
        self.kinds = {d.kind for d in plan.districts}
        self.marks = collections.defaultdict(list)
        for m in plan.landmarks:
            d = self.district_at(m.x, m.y)
            if d is not None:
                self.marks[d].append(m)
        self.shrines = collections.Counter(b.district for b in plan.buildings if b.kind == "marabout")
        self.trades = collections.defaultdict(collections.Counter)
        for h in plan.households:
            self.trades[plan.buildings[h.building].district][h.trade] += 1
        self.souks = collections.defaultdict(dict)   # district -> trade -> the souk's shortest name
        for k in plan.souks:
            mid = plan.streets[k.street].line.interpolate(0.5, normalized=True)
            d = self.district_at(mid.x, mid.y)
            if d is not None:
                names = self.souks[d]
                if k.trade not in names or len(k.name) < len(names[k.trade]):
                    names[k.trade] = k.name
        port = plan.port
        self.quays = collections.Counter()
        self.lights = set()
        if port is not None:
            for q in port.quays:
                self.quays[q.district] += q.line.length
            for bw in port.breakwaters:
                if 0 <= bw.quay < len(port.quays):
                    self.lights.add(port.quays[bw.quay].district)

    def district_at(self, x, y):
        p = Point(x, y)
        for d in self.plan.districts:
            if d.polygon.buffer(1.0).contains(p):
                return d.id
        return None

    def era(self, style, kind) -> str:
        """The era a district of this kind dates from: its style era, never before the city's founding."""
        if not self.eras:
            return ""
        want = style.get("era", {}).get(kind, "")
        if kind == "park" and "colonial" not in self.kinds:
            want = style.get("era", {}).get("park_late", want)
        k = self.eras.index(want) if want in self.eras else self.founded
        return self.eras[max(k, self.founded)]


def _history(ctx, style, facts, d) -> str:
    rng = ctx.rng("history", d.id)
    kind = d.kind
    place = {"capital": "city"}.get(ctx.s.kind, ctx.s.kind)
    era = facts.era(style, kind)
    fields = {"name": d.name, "city": ctx.s.name, "era": _era_in(style, era), "since": _era_since(style, era),
              "where": _where(facts, d), "place": place, "folk": "the village" if kind == "village" else "the neighborhood"}
    origin = style.get("origin", {}).get(kind) or style.get("origin", {}).get("residential", ["{name}."])
    if kind == "port" and facts.medina is not None and era and facts.founded < facts.eras.index(era):
        origin = style.get("origin", {}).get("port_old", origin)
        fields["old_since"] = _era_since(style, facts.eras[facts.founded])
    sentences = [_pick(rng, origin).format(**fields)]
    known = _facts(rng, style, facts, d, fields, ctx.s)
    keep = int(style.get("facts", 2))
    if len(known) > keep:
        w = [float(style.get("fact_weights", {}).get(key, 1.0)) for key, _text in known]
        idx = rng.choice(len(known), size=keep, replace=False, p=[v / sum(w) for v in w])
        known = [known[i] for i in sorted(int(i) for i in idx)]
    sentences += [text for _key, text in known]
    if len(sentences) < 3:
        today = style.get("today", {}).get(kind)
        if today:
            sentences.append(_pick(rng, today).format(**fields))
    return " ".join(_capital(s) for s in sentences[:4])


def _facts(rng, style, facts, d, fields, s) -> list:
    """(key, sentence) for each fact the map gives about this district."""
    t = {k: (_pick(rng, v) if isinstance(v, list) else v) for k, v in style.get("fact", {}).items()}
    out = []
    marks = facts.marks.get(d.id, [])
    by = collections.defaultdict(list)
    for m in marks:
        by[m.kind].append(m.name)
    if by["gate"] and "gates" in t:
        gates = by["gate"]
        key = {1: "gate", 2: "gates_all"}.get(len(gates), "gates")
        key = key if key in t else "gates"
        out.append(("gates", t[key].format(n=_number(len(gates)), some=_join(gates[:2]), **fields)))
    if by["kasbah"] and "kasbah" in t:
        out.append(("kasbah", t["kasbah"].format(kasbah=by["kasbah"][0], **fields)))
    if by["cathedral"] and by["theatre"] and "boulevard" in t:
        out.append(("boulevard", t["boulevard"].format(cathedral=by["cathedral"][0], theatre=by["theatre"][0], **fields)))
    elif (by["cathedral"] or by["theatre"]) and "civic" in t:
        out.append(("civic", t["civic"].format(civic=(by["cathedral"] + by["theatre"])[0], **fields)))
    if by["station"] and "station" in t:
        out.append(("station", t["station"].format(station=by["station"][0], **fields)))
    mosques = [n for n in by["mosque"] if not n.startswith("Great Mosque")]
    if mosques and "mosque" in t:
        out.append(("mosque", t["mosque"].format(mosque=mosques[0], **fields)))
    souks = facts.souks.get(d.id, {})
    if souks and "souks" in t:
        out.append(("souks", t["souks"].format(souks=_join(list(souks.values())[:3]), **fields)))
    if facts.shrines.get(d.id) and "shrines" in t:
        key = "shrine" if facts.shrines[d.id] == 1 and "shrine" in t else "shrines"
        out.append(("shrines", t[key].format(n=_number(facts.shrines[d.id]), **fields)))
    if facts.quays.get(d.id, 0.0) > 0 and "quays" in t:
        text = t["quays"].format(quay=f"{facts.quays[d.id]:,.0f}", **fields)
        if d.id in facts.lights and "light" in t:
            text = text[:-1] + t["light"]
        out.append(("quays", text))
        coast = [k for k in s.known_for if k in style.get("harbor_trades", [])]
        if coast and "known" in t and d.id == facts.quays.most_common(1)[0][0]:   # the main harbor only
            out.append(("known", t["known"].format(known=coast[0], **fields)))
    trades = [w for w, _n in facts.trades.get(d.id, collections.Counter()).most_common(3)]
    if len(trades) == 3 and "trades" in t:
        out.append(("trades", t["trades"].format(trades=_join([_plural(w) for w in trades]), **fields)))
    return out


def _where(facts, d) -> str:
    """Where the district lies from the old town, to end a clause (", just east of the medina"), or ""."""
    m = facts.medina
    if m is None or d is m:
        return ""
    a, b = m.polygon.centroid, d.polygon.centroid
    word = COMPASS[int(round(math.atan2(b.y - a.y, b.x - a.x) / (math.pi / 4))) % 8]
    near = "just " if d.polygon.buffer(5.0).intersects(m.polygon) else ""
    return f", {near}{word} of the medina"


def _era_in(style, era: str) -> str:
    """The era as a time phrase ("in the Caravan Age"), from the style's `era_in`; "" for no era."""
    return str(style.get("era_in", {}).get(era, f"in the time of {era}")) if era else ""


def _era_since(style, era: str) -> str:
    """The era as a "since" phrase ("since the Caravan Age"), from the style's `era_since`; "" for no era."""
    return str(style.get("era_since", {}).get(era, f"since the time of {era}")) if era else ""


def _pick(rng, seq):
    return str(seq[int(rng.integers(len(seq)))])


def _number(n: int) -> str:
    words = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
    return words[n] if n < len(words) else str(n)


def _join(items: list) -> str:
    items = [str(i) for i in items]
    if len(items) < 2:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _plural(word: str) -> str:
    return word[:-3] + "men" if word.endswith("man") else word + "s"


def _capital(sentence: str) -> str:
    return sentence[:1].upper() + sentence[1:]
