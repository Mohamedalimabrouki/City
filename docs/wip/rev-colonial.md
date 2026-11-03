# rev-colonial: review of 62bd76f (WIP colonial-k, on top of main c48fb1e)
Scope: citygen/interior/bayplan.py, program.py, spine.py, styles/maghreb.toml, tests/test_citygen.py, docs/wip/colonial-k.md.

## Verdict
No correctness or determinism bug found. Slab and every other layout keep their old path (middle off, spare 0), so only colonial flats change. No new random draws or streams; all new sorts have full keys (area, part); the one set (`seen`) is membership only. Each candidate plan has its own fresh cells list, so `reach` mutating it is safe.

## Findings (file:line, severity, one-line fix)
1. citygen/interior/bayplan.py:42, medium (numbers in toml): `stub_middle` default 12.0 lives only in code. Fix: add `stub_middle = 12.0` to the `bay_plan` table in styles/maghreb.toml:2061.
2. docs/wip/colonial-k.md:4, medium (process): the notes stop at "19:10 started": no fingerprint compare, build or test result recorded for this WIP. Fix: rerun pytest, build --quick and `fingerprint.py compare` before this is merged, and write the result there.
3. citygen/interior/bayplan.py:277-299, low: `reach` joins a blind piece to a way without checking the lit piece then has a door on the way; a join that does not help still grows the hall (up to its `most`) before the loop tries again. Fix: keep a join only if `door_on_way(job, c, cells)` is true after it, else try the next way or piece.
4. citygen/interior/bayplan.py:281, low: "room-sized" means `job.fits(c.poly, "cuisine")`, a hard-coded type. Fix: take the type from the program's smallest lit room or name it in `[interiors.flats] bay_plan`.
5. citygen/interior/bayplan.py:468-475, low: if the least hall size gives `hall is None`, the loop breaks at once and the deeper or wider sizes are never tried. Fix: `continue` on None while sizes are left (middle layouts only).
6. tests/test_citygen.py:4214-4216, low: the new first assert recomputes `flat_type` with the code's own function (cannot fail on a wrong rule); the second compares type strings ("S+1" <= "S+2"), fine only while types stay one digit. Fix: compare `int(t.split("+")[1])`.
7. tests/test_citygen.py:4945 (new test), ok: hand-made, fast, and can fail (checks the spare bay rule and that the blind piece joins the hall, not the lit room).

## Left
Not run: pytest and build on this branch (4-minute budget; check-* helpers run the suite).
