# City generator - rules for Claude

Python 3.11+ procedural generator for an invented Mediterranean / North African country.
The code builds the world; agents only improve the code. Keep every session small and cheap.

## The owner and how to work with him
- Ali is not a software developer: answer in plain language (about B2 English), define jargon,
  keep reports under 10 lines. Background and past decisions: `docs/HANDOFF.md` (read only
  when the task needs it).
- One task per session. Efficient, but never lower the quality bar below.
- Visual checks: at most two snapshots per task, then ask Ali to look (`python -m citygen view`).
- On Ali's Mac use `.venv/bin/python` instead of `python`.

## Before you code
- Read only what the task needs: the task in `docs/ROADMAP.md`, the matching parts of
  `docs/SPEC.md`, and the files the task names.
- Never open files in `output/` (huge generated data). Use `python -m citygen stats`,
  the PNG maps in `output/*/maps/`, or `python -m citygen snapshot` instead.

## Rules
- Determinism: all randomness comes from `citygen.rng.stream(seed, *purpose)`. Give each new
  feature its own purpose path. No `random` module, no unseeded numpy, no set iteration order.
- Looks and numbers live in `styles/*.toml` or `citygen/defaults.toml`, not in code.
- Units are meters; x = east, y = north, z = up. Only the glTF export converts to Y-up.
- Small functions, match the style of nearby code, no new dependencies without asking.
- Never write the em dash character anywhere; use "-".

## Check your work before committing
- `python -m pytest -q` (about 20 s) must pass.
- `python -m citygen build --quick` must finish (about 1 min). For visual changes, look at
  `output/*/maps/*.png` or run `python -m citygen snapshot --view aerial`.
- Mark the task done in `docs/ROADMAP.md`, update docs the change touches, then commit with a
  clear message and push (GitHub is the backup).
