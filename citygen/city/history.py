"""District histories (prompt 81): two to four sentences per district, for writing stories.

Built from the style's `[history]` templates and the facts of the plan only: the era the settlement
was founded in (`[lore] eras`, never earlier for a district than for its city), the district's kind,
where it lies from the old town, the landmarks inside it (gates, the kasbah, mosques, the cathedral and
the theatre, the station, a cemetery's shrines), its souks, its households' trades and its quays.
Every choice has a stream of its own ("history", district id, what it chooses), so nothing else moves and
editing one list of the style changes no other sentence. A text in the world file's
`[canon.histories."<city>"]` table, keyed by the district's name, replaces the generated one.
"""
from __future__ import annotations

import collections
import math
import warnings

from shapely.geometry import Point


def histories(ctx, plan) -> None:
    """Set `history` on every district of the plan."""
    style = ctx.style.get("history", {})
    if not style:
        return
    canon = ctx.world.cfg.get("canon", {}).get("histories", {}).get(ctx.s.name, {})
    facts = _Facts(ctx, plan, style)
    unknown = sorted(set(canon) - {d.name for d in plan.districts})
    if unknown:
        warnings.warn(f"[canon.histories.{ctx.s.name!r}] names no district of the city: {', '.join(unknown)}")
    for d in plan.districts:
        if d.name in canon:
            d.history = str(canon[d.name])
            continue
        d.history = _history(ctx, style, facts, d)


class _Facts:
    """What the map says about each district."""

    def __init__(self, ctx, plan, style):
        self.plan = plan
        self.inside = float(style.get("inside_m", 1.0))   # a point this close to a district counts as in it
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
        """The district a point lies in, else the first one within `inside_m` of it (a gate on the wall line)."""
        p = Point(x, y)
        for d in self.plan.districts:
            if d.polygon.contains(p):
                return d.id
        for d in self.plan.districts:
            if d.polygon.buffer(self.inside).contains(p):
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
    kind = d.kind
    place = str(style.get("place", {}).get(ctx.s.kind, ctx.s.kind))
    folk = style.get("folk", {})
    era = facts.era(style, kind)
    fields = {"name": d.name, "city": ctx.s.name, "era": _era_phrase(style, "era_in", era),
              "since": _era_phrase(style, "era_since", era),
              "where": _where(style, facts, d), "place": place, "folk": str(folk.get(kind, folk.get("default", "")))}
    origins = style["origin"]
    origin = origins.get(kind) or origins["residential"]
    if kind == "medina" and not ctx.kc.get("walls", True):   # an old town without walls: no ramparts in its story
        origin = origins.get("medina_open", origin)
    if kind == "port" and facts.medina is not None and era and facts.founded < facts.eras.index(era):
        origin = origins.get("port_old", origin)
        fields["old_since"] = _era_phrase(style, "era_since", facts.eras[facts.founded])
    sentences = [_pick(ctx, d, "origin", origin).format(**fields)]
    known = _facts(ctx, style, facts, d, fields)
    keep = int(style.get("facts", 2))
    if len(known) > keep:
        w = [float(style.get("fact_weights", {}).get(key, 1.0)) for key, _text in known]
        rng = ctx.rng("history", d.id, "facts")
        idx = rng.choice(len(known), size=keep, replace=False, p=[v / sum(w) for v in w])
        known = [known[i] for i in sorted(int(i) for i in idx)]
    sentences += [text for _key, text in known]
    if len(sentences) < int(style.get("min_sentences", 3)):
        today = style.get("today", {}).get(kind)
        if today:
            sentences.append(_pick(ctx, d, "today", today).format(**fields))
    return " ".join(_capital(s) for s in sentences[:int(style.get("max_sentences", 4))])


def _facts(ctx, style, facts, d, fields) -> list:
    """(key, sentence) for each fact the map gives about this district."""
    t = {k: (_pick(ctx, d, f"fact.{k}", v) if isinstance(v, list) else v) for k, v in style.get("fact", {}).items()}
    out = []
    marks = facts.marks.get(d.id, [])
    by = collections.defaultdict(list)
    for m in marks:
        by[m.kind].append(m.name)
    if by["gate"] and "gates" in t:
        gates = by["gate"]
        key = {1: "gate", 2: "gates_all"}.get(len(gates), "gates")
        key = key if key in t else "gates"
        out.append(("gates", t[key].format(n=_number(style, len(gates)), some=_join(style, gates[:2]), **fields)))
    if by["kasbah"] and "kasbah" in t:
        out.append(("kasbah", t["kasbah"].format(kasbah=by["kasbah"][0], **fields)))
    if by["cathedral"] and by["theatre"] and "boulevard" in t:
        out.append(("boulevard", t["boulevard"].format(cathedral=by["cathedral"][0], theatre=by["theatre"][0], **fields)))
    elif (by["cathedral"] or by["theatre"]) and "civic" in t:
        out.append(("civic", t["civic"].format(civic=(by["cathedral"] + by["theatre"])[0], **fields)))
    if by["station"] and "station" in t:
        out.append(("station", t["station"].format(station=by["station"][0], **fields)))
    mosques = [] if d.kind in style.get("great_mosque_kinds", []) else by["mosque"]   # not the great mosque
    if mosques and "mosque" in t:
        out.append(("mosque", t["mosque"].format(mosque=mosques[0], **fields)))
    souks = facts.souks.get(d.id, {})
    if souks and "souks" in t:
        out.append(("souks", t["souks"].format(souks=_join(style, list(souks.values())[:3]), **fields)))
    if facts.shrines.get(d.id) and "shrines" in t:
        key = "shrine" if facts.shrines[d.id] == 1 and "shrine" in t else "shrines"
        out.append(("shrines", t[key].format(n=_number(style, facts.shrines[d.id]), **fields)))
    if facts.quays.get(d.id, 0.0) > 0 and "quays" in t:
        text = t["quays"].format(quay=f"{facts.quays[d.id]:,.0f}", **fields)
        if d.id in facts.lights and "light" in t:
            text = text[:-1] + t["light"]
        out.append(("quays", text))
        coast = [k for k in ctx.s.known_for if k in style.get("harbor_trades", [])]
        if coast and "known" in t and d.id == facts.quays.most_common(1)[0][0]:   # the main harbor only
            out.append(("known", t["known"].format(known=coast[0], **fields)))
    trades = [w for w, _n in facts.trades.get(d.id, collections.Counter()).most_common(3)]
    if len(trades) == 3 and "trades" in t:
        out.append(("trades", t["trades"].format(trades=_join(style, [_plural(style, w) for w in trades]), **fields)))
    return out


def _where(style, facts, d) -> str:
    """Where the district lies from the old town, to end a clause (", just east of the medina"), or ""."""
    m = facts.medina
    compass = style.get("compass", [])
    if m is None or d is m or not compass:
        return ""
    a, b = m.polygon.centroid, d.polygon.centroid
    turn = math.atan2(b.y - a.y, b.x - a.x) / (2 * math.pi / len(compass))
    word = compass[int(round(turn)) % len(compass)]
    near = str(style.get("near_word", "")) if d.polygon.buffer(float(style.get("near_m", 5.0))).intersects(m.polygon) else ""
    return str(style.get("where", "")).format(near=near, dir=word)


def _era_phrase(style, table: str, era: str) -> str:
    """The era as the style's `table` words it ("in the Caravan Age"), or as its `<table>_default`; "" for no era."""
    if not era:
        return ""
    return str(style.get(table, {}).get(era, str(style.get(f"{table}_default", "{era}")).format(era=era)))


def _pick(ctx, d, what: str, seq) -> str:
    """One entry of a style list, on a stream of its own: editing that list changes no other choice."""
    return str(seq[int(ctx.rng("history", d.id, what).integers(len(seq)))])


def _number(style, n: int) -> str:
    """A count in words from the style's `numbers` (0 first), digits past its end."""
    words = style.get("numbers", [])
    return str(words[n]) if n < len(words) else str(n)


def _join(style, items: list) -> str:
    items = [str(i) for i in items]
    if len(items) < 2:
        return "".join(items)
    return ", ".join(items[:-1]) + str(style.get("and_word", ", ")) + items[-1]


def _plural(style, word: str) -> str:
    """The plural of a trade: the first `plural` ending that fits is swapped, else `plural_default` is added."""
    for end, plural in style.get("plural", {}).items():
        if word.endswith(end):
            return word[:-len(end)] + str(plural)
    return word + str(style.get("plural_default", "s"))


def _capital(sentence: str) -> str:
    return sentence[:1].upper() + sentence[1:]
