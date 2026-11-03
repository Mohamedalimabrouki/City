# rev-little: review of wip/fix-little (c7d7104, c9c97f4 on top of 3036039)

Scope: `git diff 3036039..HEAD -- citygen styles tests` (villa.py +2, maghreb.toml +1, test +41). 3 November, about 20:57 UTC, 4-minute review.

## Findings
1. tests/test_citygen.py:4757 (`assert time.perf_counter() - t < 1.0`), MEDIUM: the only check that can fail without the bound is this timing one. The two `is None` checks pass at HEAD without the bound too (the 15 x 20 floor found no plan before, per fix-little.md), and a 1 s limit can fail on a loaded Mac (notes say load 10-60). Fix: prove "no search ran" without a clock, for example monkeypatch `V.affinity.rotate`-later helper or count calls of the inner search (spy on `shapely` `intersection` or on `job.fits`: assert it is never called for the 15 x 20 floor), and drop the time assert.
2. tests/test_citygen.py:4763, LOW: only one blank line before `def test_relit_repartition` (the file uses two). Fix: add a blank line.
3. citygen/interior/villa.py:239, LOW (style, accepted): the fallback `1e9` in code means "no bound" when the key is missing; it matches nearby reads (villa.py:38, 184 use the same `cfg.get("villa", {}).get(key, default)` form), and the real number lives in styles/maghreb.toml:2040. No change needed; optional: put `little_most` in citygen/defaults.toml too if other styles exist.
4. citygen/interior/villa.py:239, LOW (doc): the bound tests the rotated rectangle's area, not the floor's (the docstring says so); an L-shaped floor of 50 m2 in a 90 m2 rectangle is now skipped. fix-little.md says no plan in Ain Chilel changes (794 of 794 rooms.json equal), so fine for now; note it in SPEC 6c if the rule is kept.

## Checked, no problem
- Determinism: no random draws, no new stream, no set order; the early `return None` comes before any draw (little() draws none).
- Number in toml: `little_most = 80.0` with a comment in styles/maghreb.toml; no em dash in the added lines.
- Test runtime: hand-made, well under 2 s.

## Left (no time)
- Did not run pytest or the build here (check-* helpers do that).
- Did not re-time the 80 m2 limit myself.
