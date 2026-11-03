# canon-60: why prompt 60 shifts settlement names, and a plan to keep them (read-only study, 3 November 20:53 UTC)
Worktree /tmp/claude-501/canon-60 on wip/rivers-60 (d1c5be0). No code changed.

## Why the places and names shift
- Places: `world._place_settlements` (citygen/world.py:127-196) draws everything from ONE sequential stream,
  `stream(seed, "settlements")` (world.py:147): jitter, then per kind (capital, city, town, village) a score
  grid `rng.uniform(..., size=H.shape)` (world.py:163) and keys `rng.random(score.shape)` (world.py:176), and
  one population draw per candidate TRIED (world.py:182), before the conflict / height / lake checks.
  The new lake skip (world.py:189) is after the pop draw, so it adds no draw to that candidate, but the city
  loop must then try one more candidate: one more pop draw. Every later draw of the stream (the town and
  village score grids and keys) is offset by one, so every town and village lands elsewhere (ids 0-2, drawn
  before the skip, stay; 127 of 131 move).
- Names: `generate_world` (world.py:112-115) names the settlements in id order from ONE sequential stream,
  `stream(seed, "names")`, after the country name; `NameMaker.settlement(kind)` (names.py:116) draws a
  variable count per name (core, roll, prefix, article). The k-th settlement of a kind sequence gets the k-th
  name, so names follow the id and the order, not the place: when the places move, each name now sits on
  another place (and if a kind ever fails to fill its count, every later name changes too). Worse for the
  cities after id 3: they did not really move, but each one's id drops by one, so each takes the name of the
  city before it (the name and the canon pin follow the id).
- Lore: `_add_lore` uses `stream(seed, "lore")` in id order too (world.py:219), same weakness.

## Which names are canon
- The only pin in code is `cfg["canon"]["names"]` by id (world.py:116-119). worlds/example.toml:16-20 has
  only commented examples (0 = "Carthage Nova", 12 = "Sidi Amor"); no live pin in defaults.toml or styles.
  README.md:176 promises a pin "never changes, even if the generator gets new features": false today, since a
  pin by id lands on another place after any placement change (prompts 08-stories.md:67, 102, 105 extend
  `[canon]` the same way, so fix the key before prompt 84 and 87 build on it).
- Names used as fixed facts elsewhere: the quick world's capital (id 0) and Ain Chilel (tools/interior_survey.py:9,
  docs/SPEC.md:298, 303, 1106, 1332: the quick world's villa town); Sota and Chilel in tests/test_hydro.py:77
  (64 km world) and docs/wip/rivers-59.md, rivers-60.md; WORKLOG / HANDOFF / prompts/05 mention them as history.
  The quick world is unchanged by prompt 60 (0 of 282 fingerprint parts), so its canon names are safe today.
  NOT checked (time): styles/*.toml lore text, tests that assert other names; grep the 64 km gazetteer before
  and after for the full list.

## Plan (not made: needs the 64 km before/after compare and Ali's yes, since it changes every world's names)
1. Places, so a skip only moves the skipped place (world.py:161-182): give each kind its own stream and each
   candidate its own draws: `rk = stream(seed, "settlements", kind)` for the score grid and keys, and the pop
   from `stream(seed, "settlements", kind, int(flat))` (per grid cell). Then a lake skip changes nothing
   for other candidates or kinds. This moves every settlement ONCE (new streams), so do it in the same
   prompt as the lake skip, never later.
2. Names keyed by place, not order (world.py:114-115): `NameMaker(style, stream(seed, "names", kind, cell))`
   per settlement, where `cell` = the grid cell index `flat` stored on the Settlement at placement
   (new field, not in to_json). A settlement that did not really move (same cell) keeps its name; uniqueness:
   on a clash, redraw from `stream(seed, "names", kind, cell, k)`, k = 1, 2, ...
3. Canon pins by place, not id: `[canon.names]` keys become "kind:cell" (or nearest to x,y within 1 km),
   with the id form kept for the capital only.
4. Test (tests/test_world.py, fast, quick world): build the world, then rebuild it with one extra lake or a
   candidate forced to skip (monkeypatch `in_lake` / `lake_shape` to wet one city's disc); assert every other
   settlement keeps its (x, y) and its name, and every `[canon.names]` pin still names the same place.
   A 64 km variant (slow marker): before/after names of settlements whose center moved < 50 m are equal.

## Left
- The change itself and its test (step 1-4), the full canon list from the 64 km gazetteer, the lore stream.
