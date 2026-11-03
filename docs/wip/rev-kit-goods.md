# rev-kit-goods: review of `git diff e871984..HEAD -- citygen tests styles`

Scope: one commit (9e22ff5 WIP kit-goods). `citygen/interior/weave.py` `_goods` rewritten (six product
kinds: box, tin, bottle, jar, packet, stack) and the `goods` line of `styles/maghreb.toml`. Texture only:
no mesh is touched, so normals, UVs, one-sided faces and piece names do not apply.

## Findings (file:line, severity, one-line fix)
1. citygen/interior/weave.py:363, low: the top height 0.92 is in code while `hmin` is in the toml; fix:
   `s.get("hmax", 0.92)` and `hmax = 0.92` on the goods line.
2. citygen/interior/weave.py:367, low: kind height factors 0.55 / 0.62 / 0.50 / 0.70 are in code; fix:
   `h_tin`, `h_stack`, `h_jar`, `h_bottle` keys on the goods line (shape fractions inside each kind can
   stay in code, as in the nearby makers).
3. citygen/interior/weave.py:355-356, low: if every `w_*` is 0, `weights / weights.sum()` divides by zero
   (NaN cuts, every product becomes a "stack"); fix: fall back to equal weights when the sum is 0.
4. citygen/interior/weave.py:362, low: `rng.choice(len(colors), 2, replace=False)` raises ValueError for a
   style with fewer than 2 `color_*`; fix: `replace=len(colors) < 2`.
5. Determinism, OK: all draws are on `stream(seed, "texture", "goods")` (weave.py:432), the texture's own
   stream, so the new draw pattern changes only the goods image (the point of the change). `_items`
   returns a list drawn before the loop. No set order, no `random`, no `hash(`.
6. Tests, medium: no test was added or changed; tests/test_homekit.py:81 only checks that the row tiles
   across. Fix: a test that each of the six kinds is drawn (for example with one `w_*` forced to 1 and
   the rest 0) and that a `w_*` of 0 removes that kind.
7. Materials, OK: palette, back, label and cap colours are unchanged from e871984; no new material, so
   nothing new can clash with the city's.
8. weave.py, the `elif kind == "bottle"` branch, info: the bottle cap is drawn in the accent colour, not
   in `cap`; fine, but the docstring could say so.

## Left (no time in 4 minutes)
- Sizes against SPEC 6: items are now wider (wmin 16, wmax 34 px, was 10, 26), so fewer products per
  row; check at the shelf's texture scale that a carton is not wider than a real one (about 0.25 m).
- Rendering the texture once to look at it (no image made); tests were not run by me.
