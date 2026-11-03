# rev-fix70: review of the branch's own commits (prompt 70 street graph + fix-70)

Reviewed `git diff c48fb1e..HEAD -- citygen tests docs/SPEC.md` (commits 03685f1, 8e38bab, 57c8c1d,
7cc1e2d), mainly the fix commit 7cc1e2d. Read only; tests not run here (check-* helpers do that).

## Verdict
fix-70 does what review-70 asked (Medium 1 and 2). No High or Medium findings. Mergeable.

## Findings
| # | Where | Severity | Finding | Fix (one line) |
|---|-------|----------|---------|----------------|
| 1 | tests/test_citygen.py:5104 | Low | `check=True, capture_output=True`: if a child fails, pytest shows only "exit status 1"; the child's error text is swallowed. | `r = subprocess.run(..., capture_output=True)` then `assert r.returncode == 0, r.stderr.decode()[-2000:]`. |
| 2 | citygen/defaults.toml:79 vs styles/maghreb.toml:321 | Low (naming) | Two different `[streets]` tables: defaults (graph) and style (street looks). Loaded apart (cfg vs style), so no clash today, but easy to confuse. | Rename to `[street_graph] grid = 0.05`, or keep and say "graph only" in the comment. |
| 3 | citygen/export/streets.py:34 | Low | One knob, two jobs: `graph_grid` sets the noding grid and also the impasse-mouth reach (`width/2 + grid`). Coarsening the grid widens the reach. The toml comment says so. | Accept, or a separate `mouth_reach` key later. |
| 4 | citygen/buildkey.py:63 | Info | The whole cfg is in the build key, so changing only `graph_grid` rebuilds every tile though only streets.json uses it. This commit's key changes anyway (new code). | Accept; optional later: keep `streets` out of the tile key. |
| 5 | tests/test_citygen.py:5091 | Info | The two-process test uses `Ground(w, [p])` (capital only); build.py uses `Ground(world, plans)`. It proves determinism across PYTHONHASHSEED, not equality with the build's file. | Accept (that is the rule's aim). |
| 6 | citygen/export/streets.py:16 | Info (style) | One blank line between the imports and `def center_lines`; two elsewhere. | Add a blank line. |

## Still open from review-70 (not in fix-70's scope)
- Low 5: tests/test_citygen.py:5063 `drawn - 1.0 < total` may fail on another seed (1 m slack).
- Low 6: citygen/export/streets.py:34 a mouth exactly on its host line (distance 0) gets no host vertex.
- Low 8: SPEC 6 "width (curb to curb, sidewalks included)" wording.
- Info 12: connectivity tested on the quick capital only; run it on every city before ticking C4.

## Sound
- Determinism: no random draws, no new streams, no set iteration; grid read as `float(cfg[...])`.
- World has `cfg` and `capital()` (citygen/world.py:67, 78), so the subprocess code is valid.
- The grid is threaded through center_lines, noded, street_graph; no other callers (grep).
- No em dash character in the diff.
