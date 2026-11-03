# test-villa-369 (from wip/villas-o, review-villas finding 2), 3 November

Added `test_villa_369_plan_is_valid` (`slow`) at the end of tests/test_citygen.py: it plans villa 369 of
the villa town (quick world, settlement 3, the town the `villas` fixture uses; the brief said "quick
capital", but 369 is a villa of this town, per docs/wip/villas-o.md) and asserts layout "villa" and
`rooms.check(...) == []`. It uses only the `world` fixture (no gardens), about 8 to 11 s.

Can it fail? Yes. A copy of the test run on the parent c48fb1e code (scratchpad/hy/head) fails on the
rooms.check assert ("the vil..."); on this branch it passes. Run: `pytest -q -m slow -k villa_369`.

Left: did not run the full `pytest -q` (tests only; the new test is `slow`, so `pytest -q` skips it).
