# Prompt 70 (C4a street graph) notes - helper in /tmp/claude-501/graph-70 (branch wip/graph-70)
## Plan
- new citygen/export/streets.py: streets_json(world, plan, ground) -> citygen-streets/1
- noding: set_precision(0.05) per line + unary_union(grid_size=0.05); attribute pieces to the widest street under their midpoint
- sidewalks from city/parking.walk_widths (left = side +1, right = side -1, edge oriented along its street)
- links: country road crossings of the boundary -> nearest node
- build.py write_files writes cities/<slug>/streets.json; data_files_current lists it
- SPEC 6 table row; tests in tests/test_streets_graph.py
## Status
- 19:45 baseline build --quick running, then fingerprint save before
- 19:58 module works on quick capital: 1 component (impasse mouths needed stubs + host vertex). next: timing, build.py hook, tests, SPEC
- 20:08 build.py hooked (Ground made once after plans, reused), 2 tests added (fast 0.56s, slow 4.9s) pass. next: full pytest, build, fingerprint, SPEC
- (times above were guesses; real clock: 19:49 UTC) SPEC 6 row + "Street graph" paragraph written. Running build + fingerprint compare + full pytest in background.
## Draft WORKLOG entry (lead pastes at top of docs/WORKLOG.md)
Prompt 70 (C4a street graph): new citygen/export/streets.py writes cities/<name>/streets.json (citygen-streets/1)
next to plan.json: nodes (x, y, z = Ground.surface, degree), edges (street, kind, width, sidewalks [left, right]
from walk_widths, surface, length, from, to, line), roads (country road crossings -> nearest node). Noding on a 5 cm
grid. Impasse mouths start ~0.5 m off their host street's center line (the planner starts the lane inside the
surface): without a stub the quick capital had 104 parts (largest 92.1%); with stub + host vertex: 1 part (100%).
build.py makes one Ground after planning and shares it with index.json. SPEC 6 documents the format.
## HANDOFF lessons
- unary_union(grid_size) does not node a point that lies on another line only after both are snapped separately:
  insert the meeting point as a vertex of both lines, then snap.
- impasse lanes start `mouth_overlap` m inside their street, not on its center line: graph code must bridge it.
## ROADMAP line
- [x] 70 C4a Street graph for games (cities/<name>/streets.json; quick capital: one connected part)
- 19:55 fixed ring orientation (project the 1/4 and 3/4 points, not the ends); test asserts edge direction. waiting on background build/fp/pytest (started before the fix: rerun build + fp + 2 tests after)
- 20:03 full pytest 164 passed (before ring fix); fp: only files/cities/goumosbane/streets.json added. Now rerun build+fp+new tests after ring fix
## DONE (20:07 UTC) - nothing committed, tree passes
- Files: citygen/export/streets.py (new), citygen/build.py, tests/test_citygen.py (2 tests at the end), docs/SPEC.md (section 6 row + "Street graph" paragraph)
- After ring fix: build --quick ok; fingerprint: only files/cities/goumosbane/streets.json added (283 parts, 1 changed);
  new tests pass (fast 0.56 s, slow 4.9 s); full pytest 164 passed (run before the ring-orientation fix, which only touches streets.py)
- Quick capital: 595 nodes, 720 edges, 43,729 m, ONE connected part (100%), 2 road links (0.02 / 0.03 m from their node), 173 KB
- Exact next step for the lead: review diff, paste the WORKLOG / HANDOFF / ROADMAP lines above, commit the 4 files, push.
