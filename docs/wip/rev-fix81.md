# rev-fix81: review of the branch's own commits (lore-81, review-81, fix-81)

Scope: `git diff c48fb1e..HEAD -- citygen tests` (district histories, prompt 81). Read in 4 minutes; the
toml diff (styles/maghreb.toml) was not read line by line.

Determinism: good on the whole. Own stream `ctx.rng("history", d.id)`; histories() runs last in
plan_city and only writes text, so no other stream moves. The two sets (`self.kinds`, `self.lights`)
are only used for membership tests, never iterated. Counter.most_common ties follow insertion order
(plan order), so they are stable.

Findings (file:line, severity, one-line fix):
1. citygen/city/history.py:117 (`t = {k: _pick(rng, v) ...}`), medium: one draw is made for every
   list template in `[history] fact`, in toml order, before we know which facts apply. Adding,
   removing or reordering one template in the toml shifts every later choice of that district
   (the fact sample and the "today" sentence). Fix: pick each template from its own stream,
   `ctx.rng("history", d.id, key)`, or pick lazily only for facts that are used.
2. citygen/city/history.py:91 and 93, low: words live in code ("the village", "the neighborhood",
   the "{name}." fallback, the capital -> "city" mapping). Fix: move them to `[history]` in
   styles/maghreb.toml like the other templates.
3. citygen/city/history.py:171 and 176, low: the fallback phrases "in the time of {era}" /
   "since the time of {era}" are English text in code; fine as a fallback, but say so in the toml
   comment, or require `era_in` / `era_since` for every `[lore] eras` entry and test it.
4. tests/test_citygen.py:1612, low: after fix-81 the era check is `if e in d.history`, a plain
   substring test. It no longer fails if an `era_in` phrase leaves out the era name, and an era
   name that is part of a district or landmark name would be checked by mistake. Fix: add a test
   that every era in `[lore] eras` has an `era_in` and an `era_since` entry that contains its name.
5. citygen/city/history.py:72-75 (`district_at`), low: a landmark on a shared border (inside the
   1 m buffer of two districts) goes to the lower-id district. Deterministic, but it can give the
   gate or station to the wrong side. Fix: test the unbuffered polygon first, buffer only as a
   fallback.
6. citygen/city/history.py:197 (`_plural`), low: only "-man" -> "-men" and "+s"; a trade like
   "potter" is fine, but "glass" or a word ending in "y" would read wrong. Fix: a plural table in
   the toml for the trades that need one.

Left: the toml diff (styles/maghreb.toml) and the em dash check of the new templates were not done.
