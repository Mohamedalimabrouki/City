# spec-54: prompt 54 (H2c Furnishing rules and density) against this branch (e871984)

Quick check by grep in 4 minutes; nothing was run.

## Do
1. household.py `profile`, `functions`: DONE (citygen/interior/household.py:70, :131); `[interiors.furnish.trade_tags]` in styles/*.toml:2172.
2. furnish.py: DONE (`RoomSpace` :97, `smaller` chains :462/:693, balcony doors :29, `furnish` :1254, `check` :1262).
3. Style `[interiors.furnish]`: DONE in the main (styles :2130, sizes :2169, trade_tags :2172, smaller :2179, smaller_trad :2220, roles :2225, 174 `[[interiors.furnish.rooms.*]]` slot tables). PARTLY: no `[interiors.furnish.trades]` header found (work sets may sit under another name; check).
4. Export and command: DONE (export.py:30 `write_folder(..., density)`, :74 `index.json` density; command.py:16; `--density` in __main__.py:89; view.py:34, :120 `api/interior?density=`).
5. Survey: PARTLY. Quick capital at 3 densities in WORKLOG (lines 112, 164, 257). LEFT: the full capital's 30-house sample at lived-in.
6. SPEC 6d and HANDOFF: HANDOFF DONE (HANDOFF.md:1120, :1141); SPEC 6d PARTLY (not checked line by line).

## Tests (tests/test_citygen.py)
- no_overlap :4818 (+ every layout :4828), required :4839, required_share :4853, household :4883, density :4903 (+ slab :4908), budget :4944: all PRESENT. Two-process run with `--density full` and `furniture.json`: :3749. Pass or fail not run here.
- The 2% share target is NOT met: 4.2% of rooms miss a piece (ROADMAP line 71, WORKLOG :112).

## Check / Done when
- LEFT: no output/checks/54.png or 54-slab.png found; no record of make_blend for the dar; fingerprint `--allow ""` not seen.

54 can be ticked: no, because 4.2% of rooms still miss a piece (target 2%), the full capital survey, the two look snapshots and the Blender file are left.
