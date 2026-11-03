# Review of prompt 94 (F4 styles per region), branch wip/styles-94 at bfaac0b

Independent review, 3 November, about 8 minutes. Read: CLAUDE.md, prompt 94, and
`git diff c48fb1e...HEAD -- citygen tests styles worlds docs/SPEC.md tools/fingerprint.py`.
Ran: `pytest -q tests/test_styles.py -m "slow or not slow"` (3 passed, 8 s), a pickle and copy
check of `StyledWorld`, and `load_config('worlds/example.toml')`. No build or fingerprint run here
(the WIP notes record 282 parts, 0 changed, on the default quick build).

Verdict: sound design, close to mergeable. One finding to fix before merge (1), the rest are
small or can wait.

## Findings

1. worlds/example.toml:25 and :28 - medium. The two table headers `[styles.settlements]` and
   `[styles.kinds]` are live (only their entries are comments), so `load_config("worlds/example.toml")`
   now holds `styles = {settlements = {}, kinds = {}}`; `build_key` hashes every non-build setting,
   so the example world's build key changes (full re-plan of its cache) with no regional style at
   all. The default world (defaults.toml, no `[styles]`) is unaffected.
   Fix: comment out the two headers in example.toml, or drop empty `styles` tables before hashing in
   `citygen/buildkey.py:build_key`.

2. citygen/mesh/tile.py:108-110 with citygen/styles.py:39 - medium (latent). `TileContext` keys its
   regional views by `style_label` (the file stem), while `World.city_world` keys its cache by the
   full name. Two packs with one stem (`rural` and `worlds/rural.toml`, or two `steampunk.toml` in
   different folders) would share one view: the second city silently gets the first city's style,
   and both namespaces are `rural/`, so names collide again. Fix: in `regional_names` (or
   `generate_world`) raise when two assigned styles have the same label.

3. citygen/styles.py:64 - low (latent). `StyledWorld.__getattr__` forwards every missing name to
   `self._world`, so `pickle.loads(pickle.dumps(sw))` and `copy.copy(sw)` end in RecursionError
   (checked). Nothing pickles one today (plans keep no world; workers rebuild `TileContext`), but
   the first change that does will crash in a worker. Fix: `if attr.startswith("__") or attr == "_world": raise AttributeError(attr)` at the top of `__getattr__`.

4. citygen/mesh/tile.py:768 (and the `own` list) - low. A regional city works on its own placement
   list, so its `keep_off` (tracks :885, harbor, props) and its crowd budget
   (`tile_bytes(tc.kit, mb, placements)` :883) no longer see the other cities' placements in the
   same tile, while a country city that comes later does filter the regional ones. Order-dependent
   but deterministic; rare (two cities, one tile, with tracks or a port). Fix: run `keep_off` of
   every city's zones over the merged list after the loop, or note it in SPEC 7.

5. citygen/styles.py:29-36 - low. A misspelt settlement name or kind in `[styles.settlements]` /
   `[styles.kinds]` is silently ignored (the city keeps the country style). Fix: check the keys in
   `generate_world` and raise like `World.find` does ("no settlement called ...; try citygen list").

6. citygen/config.py:47 - low. A `.toml` style path is tried relative to the current directory
   before the repository root, so the pack can depend on where the command runs. Fix: resolve
   relative paths from `ROOT` only (keep absolute ones).

7. tests/test_styles.py:48 - low. The only test of real output (two villages, two tiles, no name
   collisions, `instance_groups` parts) is `slow`, so the default `pytest -q` never runs it, and no
   test checks that the regional city is planned in its style (for example the tiny pack's
   `parapet_height` 1.2 or its palette reaching a placement's piece). Fix: keep it slow but add a
   fast check on `plan_city(world, tiny)` reading the merged style, or a smaller slow test in the
   default suite.

8. Gaps already stated in SPEC 7 (fine for this prompt, worth a ROADMAP line): interiors of a
   regional city use the country's home kit and Dresser (`citygen/interior/context.py:45`), and lod1
   masses use the country materials, so a regional city's far view and interiors show the country
   palette.

## What is sound

- Determinism: no new random streams; regional kits use the world seed; view and material order
  follow the plan order; `ground_heights` is idempotent (`on_ground` flag), so its second call on
  regional placements is harmless.
- Default world unchanged: `build_key` adds `regional` only when a regional style is named;
  `world.json` adds `"styles"` only when non-empty; fingerprint `kit/*` falls back to `make_kit`
  with `regional = ()`; `MeshBuilder.prefix` is empty; the country path of `build_tile` runs the
  same `_city_into` body, then `ground_heights` and spans in the old order.
- Build key for a regional world: the `[styles]` table is in the hashed settings and each regional
  pack's content is hashed (`_style_hash`), so editing a pack or an assignment invalidates the plan
  cache.
- No leak between cities: `regional_style` deep-copies (`deep_merge`), so the country pack is never
  mutated; `make_kit` is not cached, so the per-`TileContext` country kit that gains the namespaced
  pieces is private to that context; `namespaced` copies pieces and leaves the source kit untouched
  (tested).
- Namespacing covers tiles (materials via `MeshBuilder.prefix`, placements renamed), the kit sheet
  (`kit-sheet --world`) and fingerprint `kit/*`; the country style keeps today's names, as the
  prompt asks.
- Numbers: no new tunable numbers in code; the test pack holds its own values.
- No em dash character in the diff. SPEC section 7 and `worlds/example.toml` are documented.
