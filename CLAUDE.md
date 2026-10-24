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
- Never add draws to an existing stream (for example `rng("b", k)` in `Dresser.building`, the
  planner's sequential streams, or the shared `props` stream of `mesh/props.catalog`): new
  choices and new kit pieces get their own stream (`stream(seed, "piece", name)` for pieces).
  Adding or removing buildings shifts every later household: append new ones at the end.
- Looks and numbers live in `styles/*.toml` or `citygen/defaults.toml`, not in code.
- Units are meters; x = east, y = north, z = up. Only the glTF export converts to Y-up.
- Small functions, match the style of nearby code, no new dependencies without asking.
- Never write the em dash character anywhere; use "-".

## Check your work before committing
- `python -m pytest -q` (about 21 s here) must pass; `python -m citygen build --quick` must
  finish (about 10 s here). For visual changes, look at `output/*/maps/*.png` or a snapshot.
- Mark the task done in `docs/ROADMAP.md`, update docs the change touches, then commit only the
  files you changed (never `git add -A`) with a clear message, and push (GitHub is the backup).

## Prompt sessions ("Do prompt N", see docs/PROMPTS.md)
- Find `## N.` in `docs/prompts/*.md` (grep), read only that section and follow it. If a prompt
  in its "Needs" is not ticked in `docs/ROADMAP.md`, stop and tell Ali.
- Before coding: `build --quick`, then `python tools/fingerprint.py save before`.
- After coding: tests, `build --quick`, then `python tools/fingerprint.py compare before --allow
  "<the parts the prompt allows>"`. Fix or explain every other change.
- "Look" prompts: run exactly `.venv/bin/python tools/before_after.py --view <view> --out
  output/checks/<N>.png` as a command of its own (no `cd`, redirect or `&&`), so Ali's sandbox
  exclusion runs it outside the sandbox, where its browser can start. These are the two
  snapshots. Look at the image yourself before you report. Extra runs only to prove a look
  unchanged by their printed pixel difference (0.0) are fine; you need not look at those.
- Ali follows the progress in Blender: when the fingerprint shows `tiles/*` changes, run exactly
  `.venv/bin/python tools/make_blend.py` as a command of its own (no `cd`, redirect or `&&`, so
  Ali's sandbox exclusion matches it; Blender crashes inside the sandbox). It refreshes
  `output/<world>/<city>.blend`; name that file in your report.
  Blender may be started only by `tools/make_blend.py` and `tools/blender_kit_export.py` (kits
  modeled in Blender, prompt 38); both refuse to start it inside a sandbox. Never start Blender any
  other way (for example `blender -b ...`): inside the sandbox it crashes at start and macOS shows
  Ali a "Blender quit unexpectedly" message.
- Finish: the checks above, a new entry at the top of `docs/WORKLOG.md`, lessons in
  `docs/HANDOFF.md`, commit, push, then report to Ali in under 10 plain lines: what changed,
  what to look at and where, any doubt.
- Stuck after two honest attempts, or a choice the prompt does not settle: stop, write the
  question in `docs/WORKLOG.md` and ask Ali. Never lower the quality bar to finish.
- Prompts 1 and 2 create those two tools; until they exist, skip the steps that use them.
- If the prompt and `docs/ROADMAP.md` differ, the prompt wins. `--allow` lists name new pieces
  exactly (`kit/arcade_bay`), never `kit/*`.
- Builds other than `--quick` write to `--out output/full` (pass that folder to the tools).
- New tests add at most about 2 s to `pytest -q` (heavier ones get the `slow` marker); commands
  that write files on demand (interior, scene, runs, poster) get a test that runs them in two
  processes with different PYTHONHASHSEED and compares the bytes.
