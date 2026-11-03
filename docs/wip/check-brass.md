# check-brass: full tests and quick build on the fix-brass branch

Checked commit: d30fd69 "WIP fix-brass: notes (quick build checked)" (branch wip/fix-brass).
Run on 3 November, about 21:00 UTC, while about 20 other helpers shared the Mac (times are slow).

## Quick build
- `.venv/bin/python -m citygen build --quick`: PASS (exit 0), done in 9.9 s (10.7 s wall).
- World Bodjantouna (seed 42): 14 settlements, 14 roads; capital Goumosbane 1,668 buildings,
  449 streets; 9 tiles exported with 3 workers, 15 shared textures.

## Full tests
- `.venv/bin/python -m pytest -q`: PENDING
