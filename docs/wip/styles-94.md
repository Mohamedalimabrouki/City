# Prompt 94 (F4 styles per region) notes - worktree /tmp/claude-501/styles-94 (wip/styles-94), not committed
## Status (20:14 UTC): DONE, ready for the lead to review and commit
- Code done: citygen/styles.py (new), world.py (city_world, world.json "styles"), city/__init__.py (plan_city uses city_world),
  mesh/tile.py (TileContext.views + _regional_view, build_tile body moved to _city_into, regional city meshes with mb.prefix and
  renamed placements), mesh/builder.py (prefix), kitsheet.py + __main__.py (kit-sheet --world), tools/fingerprint.py (regional kit/*),
  buildkey.py (regional pack hashes), config.py (style_path: relative .toml from repo root).
- Tests: tests/test_styles.py (2 fast + 1 slow, all 3 pass), tests/data/tiny_style.toml, tests/data/two_styles.toml.
- Docs: SPEC section 7 "Styles per region", worlds/example.toml [styles] example.
- Fingerprint: quick + compare before --allow "" -> 282 parts, 0 changed (before buildkey/config edits; re-run at the end).
## Checks (all done)
- pytest -q: 165 passed, 11 deselected (12 min under machine load); late-edit re-run 8 passed; slow test_styles passes (~30 s).
- final build --quick + fingerprint compare before --allow "": 282 parts, 0 changed.
- two-style build --world tests/data/two_styles.toml --quick --out output/full: 14 tiles, 60 s; tile_12_5 (tiny village)
  86 of 89 materials namespaced tiny_style/, no duplicate names in any tile; maghreb village tiles none.
- kit-sheet --world tests/data/two_styles.toml: 490 pieces (245 tiny_style/). Fingerprint kit/* with regional: 245 extra parts.
- Snapshot not possible in sandbox (Chromium): lead should look (aerial of output/full two-style build, focus = tiny village).
- Next step: lead reviews the diff, runs the look, commits (files listed in git status), ticks F4 in ROADMAP, writes WORKLOG/HANDOFF from drafts below.
## WORKLOG entry draft
94 F4 Styles per region: a world file's [styles.settlements] (name or id) and [styles.kinds] give a settlement its own
style pack, merged over the country's. Planner, dressing, kit roles, palette and roofs follow it; terrain, roads, placement,
settlement names, ground and texture images stay global. Regional materials and pieces are namespaced "<style>/<name>" in
tiles, kit sheet and fingerprint kit/*; the country style keeps today's names. Fingerprint with no [styles]: no change.
## HANDOFF lessons
- To give a per-city variant of a TileContext, a shallow copy (view) with style attributes swapped is enough; the per-city
  tile body lives in mesh/tile._city_into so a regional city can run it on its own placement list.
- Regional pieces never meet keep_off/crowd checks of other cities' placements (own list per regional city).
## ROADMAP line
- [x] 94 F4 Styles per region
## Not done / next
- Interiors of a regional city still use the country's home kit (citygen/interior/context.py builds Dressers with world).
- lod1 masses use country materials; regional texture images (a pack's own [textures]) not supported.
