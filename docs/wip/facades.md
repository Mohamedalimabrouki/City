# facades (4 November): step 2 of the order in docs/WORKLOG.md

Branch `wip/facades` on main (8ea6008). Worktree `/tmp/claude-501/facades`. Tiles change: `make_blend` is the lead's.
Why: Ali's screenshot of Megine, an iron balcony under a window with a sill at 0.95 m: nobody can step out.

## 1. What to read first

- **0 balconies before a plain window** in the quick capital and in Megine (the survey below). All 2,238 iron balconies
  of the capital stand before door-windows, the 10,067 slab balconies before their own door.
- **The cream panels are proved and gone.** `docs/wip/facades-megine-panels.png` and `facades-corner.png`: same camera,
  before and after. The camera had flown into a building, as the lead read it.
- **One gate fails: `-m slow`, `test_furnish_required_share`: 46 of 2,091 rooms warned, 2.2%, bar 2% (35 of 2,082, 1.7% on
  main).** Two honest attempts, then I stopped, see section 7. The bar is not lowered and the test is not skipped. It is
  prompt 54's bar, which step 3 of the order finishes, and most of the rise is a door-window in a bath, which only the
  planner can cure (section 8).
- Colonial blocks barely move in passes (8/270, was 5). Their rooms do get light (chambres without a window 866 ->
  740), but what fails them is mostly the "only through a chambre" family, the planner's. As the brief said: not chased.

## 2. What changed, piece by piece

| Piece | What | Triangles |
|---|---|---|
| `window_door_<color>` (5) | porte-fenetre beside the generator's windows: stone frame, glass and two leaves to the floor, shutters beside the frame, head at the window's 1.18 m | 56 |
| `window_door_kit_<color>` (blue, green, brown) | the same beside the Tounes windows: their surround, cornice and louvered shutters, head line at their 1.095 m | 114 |
| their `_lit` twins (8) | automatic (`Kit._lit_pieces`, category `balcony`, `glass_dark`): the whole glass sheet lights, the lower panels stay dark | same |
| `balcony_iron`, `balcony_iron_long` | 1.2 x 0.6 m became 1.8 x 0.8 m, see below | 278 -> 374, 730 -> 826 |
| `balconnet_iron` | the balcony's rail with no slab, 0.92 m wide, 0.12 m off the wall, resting on the door-window's stone threshold | 196 |
| `window_slab_*_shut` (4) | back faces, so a closed persienne shows from the room | 56 -> 60 |

**Would a mason build it, could a person use it?** What the old balcony got wrong beside the sill:
- 1.2 m wide: the open shutters (1.56 m across) ran through the rail's side panels. Now 1.8 m, rail at +-0.87 m, shutters
  at most +-0.84 m: they fold back inside the rail. A test holds it.
- 0.6 m deep, 0.55 m to the rail: a sill for pots, not a place to stand. Now 0.8 m, 0.75 m to the rail.
- The rail (1.0 m), its bottom, the slab's edge and the wall behind were sound. The door's foot stands on the slab; the
  stone threshold lies 5 mm under the floor, buried in the slab (no flicker) and is the balconnet's foot.
- Door 0.8 m clear (the neighbours' width). Generator family 2.05 m high. **Kit family 1.91 m high: the kit window's glass
  stops at 0.9 m over the sill (1.85 m), which is low for a door, so the door's glass runs 0.06 m higher, up under the
  frame. The cornice and frame head stay exactly level; only the glass top differs.** Ali may want to look at that.
- The 0.8 m door against a 3.6 m storey is the windows' own proportion. A taller one would break "head level".

**No draw on an old stream.** `_door_window` swaps the piece name on the window's own placement. A test compares a
dresser with and without it. Over every placement of all 1,300 dressed buildings against main (a one-off script): medina
677 of 677 byte-identical; colonial: every old window where it was, 3,233 turned door-windows; modern: only the stair
windows moved, on purpose; 3 `door_narrow` house doors moved aside from the wider balconies.

**Facade openings.** A rail no longer makes an opening: the door-window does, kind `balcony`, a hole down to its floor, so
`furnish` keeps it clear as a door and the planners count it as light. The old `BESIDE` rule and the `railings` test in
`mesh.walled_in` are gone. A long balcony used to give a false opening at its middle, on a solid wall; that opening also
"lit" rooms, which is why chambres without a window rose 866 -> 889 on the first step alone. `outside.doors` never holds a
door-window (a test): it is no street door and no home entrance.

**Slab balconies: the WORKLOG's claim is wrong, nothing changed.** `tools/balcony_survey.py`: 10,067 in the capital, 8,087
in Megine, every one before its own door, 0 with a plain window in its width. `_slab_windows` gives a cell the balcony
or the window, as the code says. The door checked from inside (`output` interior 1088) and at night: both right.

**Balconnets.** `rng("balconnet", k, wall)`, two draws per street wall: the wall has them or not (`row` 0.3 + `wealth` 0.7 x
(wealth - 0.5)), at every window (`every` 0.6) or every second column, on every upper floor with no iron balcony. So a
street reads as whole facades treated alike, not noise. Off the arcade's terrace floor and clotheslines (tests). 953 in the
capital, 3,312 in Megine.

## 3. Windows: what each change gave

Measured first, on 1 in 4 colonial and slab plans: rooms needing daylight and having none, by the wall they touch.

| Dark rooms touching | Colonial | Slab |
|---|---|---|
| a party wall (neighbour under 0.6 m): no window possible | 88 | 0 |
| a street wall, ground floor | 44 | 0 |
| a street wall, upper floor | 13 | 0 |
| a court wall of 1.8 m or more | 24 | 0 |
| a court wall under 1.8 m | 15 | 0 |
| an open short end (gable) | 1 | 101 |
| no outside wall at all: the planner | 41 | 32 |

So windows can reach the gables, the ground floors and the street gaps. The party walls and the inner rooms stay for the
planner. Maisons (Ain Chilel) are nearly all party walls and are not colonial: unchanged. Each change alone, on the
quick capital, from the first step's 6/270 and 253/353:

| Change | Stream | Group | Pass | "chambre has no window" |
|---|---|---|---|---|
| main | | colonial / slab | 5 / 253 | 866 / 307 |
| door-windows, balconnets | | colonial / slab | 6 / 253 | 889 / 307 |
| slab gables, `gable_windows` 3.2 m | `rng("gable", k)` | slab | **281** | **130** |
| ground floors, `[dressing.ground_windows]` | `rng("ground", k)` | colonial | 3 | 783 |
| street gaps, `[dressing.fill]` | `rng("fill", k, wall, floor, i)` | colonial | 9 | 869 |
| short court walls, `short` 1.2 m | `rng("court-short", k)` | colonial | 6 | 889 |
| all of them | | colonial / slab | **8 / 281** | **740 / 130** |

The ground floors alone lose passes (6 -> 3): rooms gain light, and plans shift into the "only through a chambre" family.
Together the group still gains. Traditional houses are untouched: they still look inward (medina byte-identical).

Interior survey, before -> after (quick capital; villas and maisons in Ain Chilel):

| Group | Before | After | Ladder warnings |
|---|---|---|---|
| dar | 155/159 | 155/159 | 1 -> 1 |
| compact | 266/277 | 266/277 | 11 -> 11 |
| small | 81/83 | 81/83 | 1 -> 1 |
| koubba | 21/22 | 21/22 | 0 -> 0 |
| shop | 130/136 | 130/136 | 5 -> 5 |
| colonial | 5/270 | 8/270 | 42 -> 42 |
| slab | 253/353 | 281/353 | **44 -> 56** |
| maison | 499/616 | 499/616 | 16 -> 16 |
| villa | 168/178 | 168/178 | 3 -> 3 |

No group got worse in passes. The slab's ladder warnings rose with the gables: step 3's ladder check should look at it.
A crash this round found: No. 915, `bayplan.along`, a sliver line in an overlay ("mixed-dimension"), a bug that was
waiting there; fixed with `polygonal`, which leaves every polygon as it was.

## 4. The cream panels (question from Ali's picture)

**Proved.** `docs/wip/facades-megine-panels.png`, on Ali's own world and city, and `facades-corner.png`: left, main, cream
rectangles with brown or yellow edges and floating rails; right, the same camera. The camera stands inside a building.
Its walls are one-sided, so they vanish, and the pieces on them stay. The cream is the back of the `stone_frame` box of
the procedural `window()` (the kit's are one-sided), the colored edges its shutters. In a colonial block the slabs and
rails float too. My door-windows made it no better: their side faces showed as lines.

**The answer, viewer only, nothing in a tile.** Backs that vanish would not have done: slabs and rails are honestly
two-sided. A camera rule would jump, and seeing through a wall into the street is useful when orbiting. So a piece on a
wall (`ON_WALL`, by name) is drawn only for a camera on its wall's street side, or more than 80 m behind that wall's
plane, where a balcony may peek past a roof: a few lines in the vertex shader, `streetSideOnly`. Shadows stay. An interior
keeps every piece, since a room looks at its rail from behind the wall (`!interior`). Cost: one more material per look on
wall pieces. Blender is not concerned: its walls are not culled.

## 5. Question 15: the three old doubts

1. **The `interior` tab opens on a wall (No. 845): already settled, closed.** 2ac52f7: Open interior goes to `cut=0`, the
   overview cut at the ground floor (`tools/viewer/index.html` `offerInterior`).
2. **Light slots of 0.3 m by stair windows: fixed.** They were all on slabs (242 on 58 plans, 0 elsewhere): a stair
   window's head crossed the next slab, and the slab stopped short of the wall, a hole a foot can fall in, no railing.
   `stair_window` 0.55 -> 0.25 m: the window stands over the half landing, its head at 2.65 m, under the slab at 2.75 m.
   0 slots now on the same 58 plans; a test holds it. `floors.slots` stays for what may come.
3. **A closed slab persienne is one-sided from inside: fixed.** Two back faces at 0.06 m, which `seen_from_inside` keeps.

## 6. Gates

| Gate | Result |
|---|---|
| `pytest -q` | 216 passed, 16 deselected |
| `pytest -q -m slow` | 14 passed, 1 xfailed, **1 failed** (`test_furnish_required_share`, section 7) |
| `build --quick`, `--force` | pass, 8 s |
| two hash seeds, whole quick builds | every fingerprint part the same, tiles' sha identical |
| `fingerprint compare before --allow` | 300 parts, 32 changed, all allowed, exit 0: `tiles/*`, `kit/balconnet_iron`, `kit/balcony_iron`, `kit/balcony_iron_long`, the 4 `kit/window_slab_*_shut`, the 16 `kit/window_door_*`. `tiles/index` is 1 byte longer, a number's width |
| `tools/balcony_survey.py` | quick capital: 953 balconnets, 1,831 + 407 balconies, all before door-windows, 0 plain, 0 door-window without a rail. Megine: 3,312, 6,034 + 1,236, the same |
| rails against walls | 3,191 rails: none cuts a building, none overlaps another |
| no em dash | `git grep` 0 |

Each new test was shown to fail without its rule, by mutating a clean copy (11 mutations, all fail): door-window kept a
window; a rail counted as an opening; balconnets on the terrace; balconnets on clotheslines; door-window moved; category
`window`; balcony 1.2 m wide; no lit twin; gables on the old stream; stair window high; persienne back gone.
Tests added: 7, about 4 s on this machine; the capital-wide one is 2.2 s when nothing else runs, over the 2 s rule, kept
because the brief asks for the real capital.

**Triangle budgets** (the quick capital, own triangles of a tile -> with its instances):

| Tile | Own | Drawn | Size |
|---|---|---|---|
| 13_23 (densest) | 135,958 -> 137,590 | 2,093,318 -> 2,342,514 | 4.85 -> 4.93 MB |
| 13_24 | 45,922 -> 47,759 | 891,831 -> 1,201,647 | 1.65 -> 1.74 MB |
| 14_24 | 53,744 -> 55,376 | 530,996 -> 685,228 | 1.80 -> 1.87 MB |
| all 9 | | 5.32 M -> 6.21 M, +17% | |

Most of the rise is the 14,000 gable windows. `gable_windows` 3.2 -> 4.3 m would save about a quarter of them, at a cost
in rooms: not tried.

## 7. The slow test

`test_furnish_required_share`: 35/2,082 on main, 48/2,093 after this round. Causes, by a one-off diff of the warnings: a
door-window in a wc or sdb (8 rooms): the door keep-clear left no wall. New windows beside a basin (sdb "no basin" 2 ->
6), and small plans that moved ("wc has no wc" 4 -> 7, slab 0 -> 4).
- Attempt 1, kept: in a wet room a door-window keeps clear like a window, since nobody steps out of a bath. 48 -> 44.
- Attempt 2, dropped: a basin may stand under a window, as a sink does. No effect.
With the arcade windows it reads 46/2,091. Needed: 41. The honest cure is section 8's first rule. The lead's call: hold
the merge on it, or take it into step 3, where prompt 54 is to be finished anyway.

## 8. What Phase 3 (the interiors on these buildings) must add

The room behind a balcony door, today (1 plan in 4 of the capital):

| Room | Colonial door-windows | Slab doors |
|---|---|---|
| chambre | 327 | 1,466 |
| salon | 287 | 664 |
| salle a manger | 57 | 335 |
| cuisine | 60 | 440 |
| hall | 81 | 26 |
| couloir, droj | 51 | 7 |
| **sdb, wc** | **34** | **57** |

- The room behind a balcony is a salon or a chambre; a kitchen for a service balcony; never a bath. In colonial blocks,
  also no hall, couloir or droj where another cell can take it. `typical_key` and `bay_plan` treat a colonial balcony
  door as a window, so the planner must stop that first.
- Furniture keeps the door clear: `DOORS` holds `balcony` already; check it once baths are gone, and drop my wet-room
  exception in `_keeps` with them.
- A curtain to the floor on door-windows (SPEC 6d says it for balcony doors).
- Party walls: 88 dark rooms in the sample have no possible window: planner, or courts.

## 9. Pictures (same cameras, `tools/snapshot.py`, sandbox off; night by `--gpu`)

| File | Shows |
|---|---|
| `docs/wip/facades-street.png` | a colonial street close up, before and after: both window families in one picture |
| `docs/wip/facades-corner.png` | a street corner, camera inside a building: cream panels gone, rhythm of the street |
| `docs/wip/facades-megine-panels.png` | Megine (64 km world, `--area city:Megine`, 2.5 min), same panels. Ali's own camera is not known; his build dates from 24 October and his corner may have moved, so this is one nearby |
| `docs/wip/facades-night.png` | night, GPU: lit upper glass over dark panels. A wall lamp in the foreground on the left is a piece seen through a wall, gone on the right |
| `docs/wip/facades-gable.png` | slab ends with their windows |
| `docs/wip/facades-room.png` | from a salon of No. 845 through a door-window: the rail, the slab, the threshold |

My verdict on them: the head line, the frame's foot on the slab and the shutters inside the rail are right, up close too.
Weak: windows under arches fall where the pillars let them, so some bays stay blank (columns follow the floors above, not
the arches). Shutters of a generator door-window start beside the frame, 0.1 m further out than on the window next to it,
which hides its frame: not visible from the street, and the door would melt into them otherwise.

## 10. For the lead's docs

**WORKLOG (entry):**
```
## 2026-11-04 - Facades (step 2 of the order)
- Branch wip/facades on 8ea6008, notes docs/wip/facades.md.
- Changed: dressing.py, props.py, kit.py, outside.py, mesh.py, plancheck.py, dar.py, bayplan.py, furnish.py, viewer,
  styles, SPEC, tests, tools/balcony_survey.py (new).
- Every iron balcony stands before a porte-fenetre (2,238 in the quick capital, 0 before a plain window); balconies 1.8 x
  0.8 m so the shutters fold inside the rail; 953 balconnets; windows on slab gables (slab 253 -> 281), colonial ground
  floors and street gaps, short court walls (colonial 5 -> 8, chambres without a window 866 -> 740). Slab balconies had
  their own door: the claim above was wrong. Cream panels proved (camera inside a building) and cured in the viewer: a wall
  piece shows only from its wall's side. Question 15 closed (tab: 2ac52f7; light slots gone, stair windows under the
  slab; closed persiennes have a back).
- Checks: pytest 216; slow: test_furnish_required_share 2.2%, bar 2% (1.7% on main), door-windows in baths; fingerprint
  32 parts, all named; hash seeds identical; drawn triangles +17%.
- Look: docs/wip/facades-*.png.
- Doubts: kit-family door 1.91 m high, its glass 0.06 m above the neighbours'.
```
**ROADMAP:** no prompt to tick: this is the facade round of the order. Question 15 is closed.

**HANDOFF (lessons):**
- A rule test sees what its rule says: a balcony "stood in front of its window" by distance for 40 prompts. Ask who uses the
  thing. Count what stands behind each piece over a whole city (`tools/balcony_survey.py`).
- Pieces placed last can still change what is placed first without a draw: rename the placement in place.
- One-sided walls and wall pieces: what floats from behind is cured in the viewer's vertex shader, by the instance's front,
  not by cutting the pieces, which the interiors see from the room.
- A window is measured against the rooms: class dark rooms by the wall they touch before adding any. It showed gables
  (slab) and party walls (colonial, none possible) at once.
- `solid()` snaps to the grid; `polygonal()` leaves a polygon as it is: use it to guard an overlay without moving a plan.
