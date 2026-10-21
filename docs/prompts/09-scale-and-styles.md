# Prompts 92-100: scale, new styles, finish

Read only the section of your prompt. `CLAUDE.md` gives the routine every prompt follows.
Prompts 92-98 can be postponed; prompts 99 and 100 adapt to what is done.

## 92. E2 - Faster terrain

Model: Sonnet | Effort: high | Size: M | Needs: 1 | Look: no

**Do.**
1. Profile first: `cProfile` on `build --area capital --workers 1 --out output/full`; write the
   top 15 hot spots in your WORKLOG entry.
2. Cache exact repeated evaluations (the same points asked again by the terrain mesh, ribbons,
   the ground function and the dressing) and vectorize hot paths (Perlin and fractal noise over
   whole arrays, no Python loops per point). Never interpolate where today's code evaluates
   exactly: outputs must stay byte-identical.
3. If the profile shows that 2x needs a different ground (for example a coarser blur lattice),
   stop and ask Ali: that is its own prompt with `--allow "tiles/*"`.

**Check.** Fingerprint: no change at all (`--allow ""`), on `--quick` and on the full capital.

**Done when.** Country generation and tile building are at least 2x faster (measured before and
after, in WORKLOG and SPEC section 8), or Ali decided after your question. Tick E2.

## 93. E1 - Whole-country builds

Model: Sonnet | Effort: high | Size: M | Needs: 5, 41, 92 | Look: aerial (lod)

**Do.**
1. `--area all` plans every settlement (in parallel, like tiles) and builds every tile with
   workers, resume and LOD. Workers load the cached plans of prompt 5, and only those touching
   their tiles (never re-plan all settlements per worker); report peak memory per worker.
2. A 64 km country is 15,625 tiles: add lod2 super-tiles (8 x 8 tiles, terrain at a 128 m step,
   block masses only) to the index. The viewer shows lod2 beyond about 4 km, lod1 up to 1.5 km
   and full tiles near the camera.
3. Before the full run: `df -h`, estimate the size from a 10 x 10 km box build, and stop if it
   would exceed half the free space. Run the 64 km country in the background with
   `--out output/full`, report disk size and time, and estimate (do not run) 128 km and 256 km
   from the measured rates. Write the results in SPEC section 8.

**Check.** Fingerprint: `--allow ""` on the default quick build.

**Done when.** A full 64 km build completes, its size and time are documented, and the viewer
flies over the whole country smoothly. Tick E1.

## 94. F4 - Styles per region

Model: Opus | Effort: medium | Size: M | Needs: 1 | Look: aerial

**Goal.** A world file can give a style pack per region or per settlement (for example a
steampunk inventors' city in the mountains) instead of one style for the whole country.

**Do.** Design and implement: how a world file assigns styles (by settlement name, by kind, by
region from prompt 68 if done), how the planner, the dressing, the kit roles and the palette pick
the settlement's style, and what stays global (terrain, roads, names unless the style overrides
them). Styles collide by name today (glTF material names are palette names, Blender merges
materials with equal names, `instance_groups` keys pieces by name, and `TileContext` builds one
kit from one palette): each non-default style gets its own kit, and its materials and procedural
pieces are namespaced (`steampunk/brass`, `steampunk/tree_broadleaf`) wherever styles can meet
(tiles, kit sheet, fingerprint `kit/*`). The default style keeps today's names. Tests with a tiny
second style. Document it in SPEC section 7 and `worlds/example.toml`.

**Check.** Fingerprint: with no per-region styles in the world file, no change at all.

**Done when.** A test world with two styles builds, each city in its own style, with no name
collisions in tiles or Blender. Tick F4.

## 95. F2 - Medieval fantasy town

Model: Sonnet | Effort: high | Size: L | Needs: 94 | Look: aerial (after only)

**Do.** A style pack `styles/fantasy.toml` and its pieces: a castle on the highest hill instead
of the great mosque, steep tiled roofs, timber-framed wall textures (the texture code of prompt
18), round towers with cone roofs, forests (the tree code of Q1); it reuses walls, gates and
old-town streets as they are. A world file `worlds/fantasy.toml` that uses it.

**Check.** Fingerprint: `--allow ""` on the default quick build. Look: the HEAD tree has no
fantasy style, so take one or two after-only pictures with `python -m citygen snapshot` on a
`--world worlds/fantasy.toml --quick --out output/styles` build.

**Done when.** A fantasy town builds and reads clearly from the air. Tick F2.

## 96. F1a - Steampunk Maghreb: the style pack

Model: Sonnet | Effort: high | Size: M | Needs: 94 | Look: street (after only)

**Do.** `styles/steampunk.toml`: brass and copper domes, copper screens over windows (new
pieces, namespaced as in prompt 94), riveted iron and brass palette and textures, a clock-tower
landmark, chimney stacks on roofs; a world file that puts one steampunk city in the mountains
(prompt 94).

**Check.** Fingerprint: `--allow ""` on the default quick build. Look: after-only pictures with
`python -m citygen snapshot` on that world's build (`--out output/styles`).

**Done when.** The steampunk city reads as the same Maghreb, reimagined.

## 97. F1b - Steampunk machines

Model: Sonnet | Effort: high | Size: M | Needs: 96, 62 | Look: aerial (after only)

**Do.** Static smoke plumes from chimneys (soft translucent clumps), steam trams on rails laid
along the boulevard (reuse the rail ribbons of prompt 33's station tracks), airships moored to
minarets, canals and iron bridges along the rivers of prompts 59-62.

**Check.** Fingerprint: `--allow ""` on the default quick build. Look: after-only pictures of
the steampunk world's build.

**Done when.** The steampunk city is alive from the air and the street. Tick F1.

## 98. F3 - Two-level city: the design

Model: Opus | Effort: high | Size: L (plan) | Needs: 94 | Look: no

**Do.** Design only (an Arcane-like upper city on platforms and bridges between towers, above a
dark undercity of pipes and lanes): the vertical planning module, how platforms and bridges are
planned, stacked tiles, navigation, the viewer. Write a SPEC section and split the work into new
prompts 101 and up in a new file `docs/prompts/10-two-level-city.md` (same format), each doable
in one Sonnet session; add them to docs/PROMPTS.md and to the docs/ROADMAP.md checklist.

**Done when.** The design and the new prompts are written; Ali gets a 10-line summary.

## 99. G1 - Gallery, guide and phone page

Model: Sonnet | Effort: medium | Size: M | Needs: 57, 42 | Look: renders

**Do.**
1. Golden-hour Blender beauty renders (aerial, a souk, the boulevard, the corniche, an interior,
   a hero scene, and the steampunk city if prompt 97 is done) as small JPEGs (under 400 KB each)
   in `docs/gallery/`, committed. Add `corniche` (and any other index view) to
   `blender_beauty.py`'s `--view` choices, reading the cameras from the index views.
2. Rewrite `README.md` in plain language for a newcomer: what this is, how to run it, what you
   can make (3D cities, maps, posters, games, stories), with the gallery images.
3. Refresh the phone page as in prompt 42.

**Check.** Fingerprint: `--allow ""`.

**Done when.** The README alone sells the project, and the phone page shows the latest city.
Tick G1.

## 100. CP9 - Final review

Model: Opus | Effort: high | Size: review | Needs: 1-91, 99 | Look: everything

The last checkpoint before Ali brings the work back to his lead session. Prompts 92-98 may be
postponed; review whatever is done.
1. Run the checkpoint routine of prompt 6 for every prompt since `cp8`.
2. Whole-project review: tests and budgets (SPEC section 8), docs that tell the truth (SPEC,
   HANDOFF, README, ROADMAP ticks), code health (dead code, duplicated helpers, long functions),
   a determinism audit (grep for randomness outside `rng.stream`; streams shared by new
   features), a full `--area capital --out output/full` build with timings, the gallery.
3. Write `docs/REVIEW.md`: what is world-class, what is not yet, and the next 20 tasks with
   suggested prompts.
4. Commit, push, and report to Ali in under 15 plain lines.
