# scan-streams: new stream( purpose paths and draws per wip branch

Scan of `git diff main...origin/wip/<b> -- '*.py'` (added lines only). 'new purpose' = an added `stream(` call;
'draw, check' = an added draw call (`.random(`, `.integers(`, `.choice(` ...) in a hunk that adds no `stream(`:
it may be a new draw on an existing stream (rule break) or a draw on a stream made a few lines above; check by hand.

## arabic-87

| where | kind | text |
|---|---|---|
| citygen/names.py:149 | draw, check | `i = int(self.rng.integers(len(seq)))` |
| citygen/names.py:159 | draw, check | `coda = self._part("codas") if self.rng.random() < coda_chance else ("", "")` |
| tests/test_citygen.py:5077 | new purpose | `5, "names-ar"))` |
| tests/test_citygen.py:5078 | new purpose | `5, "names-ar"))` |
| tests/test_citygen.py:5092 | new purpose | `5, "names-ar"))` |

## canon-60

| where | kind | text |
|---|---|---|
| tests/test_hydro.py:38 | new purpose | `world):` |

## fix-59

| where | kind | text |
|---|---|---|
| tests/test_hydro.py:38 | new purpose | `world):` |

## fix-81

| where | kind | text |
|---|---|---|
| citygen/city/history.py:104 | draw, check | `idx = rng.choice(len(known), size=keep, replace=False, p=[v / sum(w) for v in w])` |
| citygen/city/history.py:180 | draw, check | `return str(seq[int(rng.integers(len(seq)))])` |

## fix-81b

| where | kind | text |
|---|---|---|
| citygen/city/history.py:109 | draw, check | `idx = rng.choice(len(known), size=keep, replace=False, p=[v / sum(w) for v in w])` |
| citygen/city/history.py:187 | draw, check | `return str(seq[int(rng.integers(len(seq)))])` |

## fix-87

| where | kind | text |
|---|---|---|
| citygen/names.py:151 | draw, check | `i = int(self.rng.integers(len(seq)))` |
| citygen/names.py:161 | draw, check | `coda = self._part("codas") if self.rng.random() < coda_chance else ("", "")` |
| tests/test_citygen.py:5077 | new purpose | `5, "names-ar"))` |
| tests/test_citygen.py:5078 | new purpose | `5, "names-ar"))` |
| tests/test_citygen.py:5092 | new purpose | `5, "names-ar"))` |

## fix-94

| where | kind | text |
|---|---|---|
| citygen/mesh/tile.py:836 | new purpose | `tc.world.seed, plan.settlement.id, int(k)), tc.roofs)` |

## fix-hide

| where | kind | text |
|---|---|---|
| citygen/interior/kit_old.py:853 | draw, check | `out.append(((p[0] + q[0]) / 2 * rng.uniform(1.05, 1.18), (p[1] + q[1]) / 2))` |
| citygen/interior/kit_old.py:856 | draw, check | `locks = [out] + [(out + (nxt - out) * f) * k * rng.uniform(0.97, 1.03, (len(out), 1)) for ` |
| citygen/interior/kit_old.py:857 | draw, check | `out = np.stack(locks, axis=1).reshape(-1, 2) + rng.uniform(-0.02, 0.02, (3 * len(out), 2))` |
| citygen/interior/kit_old.py:860 | draw, check | `edge = RUG_Z + rng.uniform(0.002, 0.006, m)               # the ragged hem, some locks lif` |
| citygen/interior/kit_old.py:862 | draw, check | `ring = np.c_[out * 0.55 * [w, d], RUG_Z + (0.7 + rng.uniform(-0.1, 0.1, m)) * (crown - RUG` |

## furn-55

| where | kind | text |
|---|---|---|
| citygen/interior/kit_life.py:282 | new purpose | `seed, "piece", f"home/{name}")` |

## furn-55b

| where | kind | text |
|---|---|---|
| citygen/interior/kit_life.py:351 | new purpose | `seed, "piece", f"home/{name}")` |

## kit-goods

| where | kind | text |
|---|---|---|
| citygen/interior/weave.py:361 | draw, check | `kind = GOODS_KINDS[int(np.searchsorted(cuts, rng.uniform()))]` |
| citygen/interior/weave.py:362 | draw, check | `i, j = rng.choice(len(colors), 2, replace=False)` |
| citygen/interior/weave.py:363 | draw, check | `run = [kind, colors[int(i)], colors[int(j)], float(rng.uniform(float(s.get("hmin", 0.5)), ` |
| citygen/interior/weave.py:364 | draw, check | `left = int(rng.integers(int(s.get("facing_min", 2)), int(s.get("facing_max", 4)) + 1))` |

## kit-hide

| where | kind | text |
|---|---|---|
| citygen/interior/kit_old.py:853 | draw, check | `out.append(((p[0] + q[0]) / 2 * rng.uniform(1.05, 1.18), (p[1] + q[1]) / 2))` |
| citygen/interior/kit_old.py:854 | draw, check | `out = np.array(out) + rng.uniform(-0.035, 0.035, (len(out), 2))` |
| citygen/interior/kit_old.py:858 | draw, check | `inner = np.c_[0.2 * np.cos(corner), 0.24 * np.sin(corner)] + rng.uniform(-0.03, 0.03, (4, ` |
| citygen/interior/kit_old.py:859 | draw, check | `edge = RUG_Z + rng.uniform(0.0015, 0.004, m)              # the ragged hem, some locks lif` |
| citygen/interior/kit_old.py:861 | draw, check | `pos = np.concatenate([np.c_[out * [w, d], edge], np.c_[inner * [w, d], crown - rng.uniform` |

## lore-81

| where | kind | text |
|---|---|---|
| citygen/city/history.py:103 | draw, check | `idx = rng.choice(len(known), size=keep, replace=False, p=[v / sum(w) for v in w])` |
| citygen/city/history.py:166 | draw, check | `return str(seq[int(rng.integers(len(seq)))])` |

## review-55

| where | kind | text |
|---|---|---|
| citygen/interior/kit_life.py:282 | new purpose | `seed, "piece", f"home/{name}")` |

## review-59

| where | kind | text |
|---|---|---|
| tests/test_hydro.py:38 | new purpose | `world):` |

## review-81

| where | kind | text |
|---|---|---|
| citygen/city/history.py:103 | draw, check | `idx = rng.choice(len(known), size=keep, replace=False, p=[v / sum(w) for v in w])` |
| citygen/city/history.py:166 | draw, check | `return str(seq[int(rng.integers(len(seq)))])` |

## review-87

| where | kind | text |
|---|---|---|
| citygen/names.py:149 | draw, check | `i = int(self.rng.integers(len(seq)))` |
| citygen/names.py:159 | draw, check | `coda = self._part("codas") if self.rng.random() < coda_chance else ("", "")` |
| tests/test_citygen.py:5077 | new purpose | `5, "names-ar"))` |
| tests/test_citygen.py:5078 | new purpose | `5, "names-ar"))` |
| tests/test_citygen.py:5092 | new purpose | `5, "names-ar"))` |

## review-94

| where | kind | text |
|---|---|---|
| citygen/mesh/tile.py:836 | new purpose | `tc.world.seed, plan.settlement.id, int(k)), tc.roofs)` |

## rivers-59

| where | kind | text |
|---|---|---|
| tests/test_hydro.py:38 | new purpose | `world):` |

## rivers-60

| where | kind | text |
|---|---|---|
| tests/test_hydro.py:38 | new purpose | `world):` |

## shot-55

| where | kind | text |
|---|---|---|
| citygen/interior/kit_life.py:282 | new purpose | `seed, "piece", f"home/{name}")` |

## shot-goods

| where | kind | text |
|---|---|---|
| citygen/interior/weave.py:361 | draw, check | `kind = GOODS_KINDS[int(np.searchsorted(cuts, rng.uniform()))]` |
| citygen/interior/weave.py:362 | draw, check | `i, j = rng.choice(len(colors), 2, replace=False)` |
| citygen/interior/weave.py:363 | draw, check | `run = [kind, colors[int(i)], colors[int(j)], float(rng.uniform(float(s.get("hmin", 0.5)), ` |
| citygen/interior/weave.py:364 | draw, check | `left = int(rng.integers(int(s.get("facing_min", 2)), int(s.get("facing_max", 4)) + 1))` |

## shot-hide

| where | kind | text |
|---|---|---|
| citygen/interior/kit_old.py:853 | draw, check | `out.append(((p[0] + q[0]) / 2 * rng.uniform(1.05, 1.18), (p[1] + q[1]) / 2))` |
| citygen/interior/kit_old.py:854 | draw, check | `out = np.array(out) + rng.uniform(-0.035, 0.035, (len(out), 2))` |
| citygen/interior/kit_old.py:858 | draw, check | `inner = np.c_[0.2 * np.cos(corner), 0.24 * np.sin(corner)] + rng.uniform(-0.03, 0.03, (4, ` |
| citygen/interior/kit_old.py:859 | draw, check | `edge = RUG_Z + rng.uniform(0.0015, 0.004, m)              # the ragged hem, some locks lif` |
| citygen/interior/kit_old.py:861 | draw, check | `pos = np.concatenate([np.c_[out * [w, d], edge], np.c_[inner * [w, d], crown - rng.uniform` |

## styles-94

| where | kind | text |
|---|---|---|
| citygen/mesh/tile.py:836 | new purpose | `tc.world.seed, plan.settlement.id, int(k)), tc.roofs)` |

## Branches with no new stream( and no added draw in .py files

47.1-48.1, 47.2-round-c, 51-furnishing, check-70, check-k, colonial-k, fix-70, fix-brass, fix-little, fix-materials, fix-textile, flats-j, furnish-m, godot-72, graph-70, houses-patio, kit-brass, kit-textile, lead-notes, merge-map, merge-prep, review-70, review-godot, review-mats, review-mp-flats, review-mp-furnish, review-mp-speed, review-patio, review-villas, shot-brass, shot-textile, speed-n, villas-o
## Traced by hand after the first push
- `citygen/names.py` (arabic-87, fix-87, review-87): OK, low. The new `_pick_i` / `_part` keep one `self.rng.integers`
  per pick and the same `self.rng.random()` coda test as main's `_pick`, so no draw is added to the naming stream.
- `citygen/city/history.py` (fix-81, fix-81b, lore-81, review-81): OK. New file; its draws use its own purpose
  `ctx.rng("history", d.id)` (history.py:89), which this scan's `stream(` search did not catch.

## Left (not done in the 4 minutes)
- kit-hide / fix-hide / shot-hide (`kit_old.py:853-862`) and kit-goods / shot-goods (`weave.py:361-364`): the `rng`
  is made outside the hunk; confirm it is the piece's own `stream(seed, "piece", name)` and not the shared `props` stream.
- Only `*.py` files were scanned; `ctx.rng(` purposes were not listed for every branch.
