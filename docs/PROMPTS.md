# Ready prompts - one new session per task

**How to use.** For every task, start a new session in the `City` folder (or type `/clear`).
Type the two settings lines first, then paste the prompt. The prompts are short on purpose:
`CLAUDE.md` is read automatically in every session and holds the quality bar (tests, build,
docs, roadmap tick, push), and `docs/HANDOFF.md` holds everything decided so far.

After a task: look at the result yourself (`python -m citygen view`, or Blender), and if something
looks wrong, say it in one or two sentences in the same session. Then start the next task in a
new session.

## 0. First session on the Mac (once)

```
/model sonnet
/effort low
```
```
Read docs/HANDOFF.md. Check that this Mac can run the project: run the tests and a quick build with .venv/bin/python, and tell me in five short lines whether everything works. Do not change any code.
```

## The tasks, in the suggested order

Normal tasks use these settings:
```
/model sonnet
/effort medium
```

| # | Task | What you will see | Prompt |
|---|---|---|---|
| 1 | Q2 Family names | names that sound real when you click a house | `Do task Q2 from docs/ROADMAP.md.` |
| 2 | Q1 Natural leafy trees | softer, natural trees on the boulevard | `Do task Q1 from docs/ROADMAP.md.` |
| 3 | Q3 Generated bougainvillea | no more "lollipop" flowers | `Do task Q3 from docs/ROADMAP.md.` |
| 4 | C1 Fast, resumable builds | big builds in minutes, restart where they stopped | `Do task C1 from docs/ROADMAP.md.` |
| 5 | H1 Interiors on demand | rooms behind the doors (big task: see below) | see below |
| 6 | H2 Furnishing | furniture inside the rooms (big task: see below) | see below |
| 7 | H3 Street life, part 2 | parked cars, benches, kiosks, seaside cafes | `Do task H3 from docs/ROADMAP.md.` |
| 8 | H4 Hero scenes | one street or house at full detail for a film shot | `Do task H4 from docs/ROADMAP.md.` |
| 9 | A4 Terrain grading | streets and doors sit cleanly on the ground | `Do task A4 from docs/ROADMAP.md.` |
| 10 | A3 Sidewalks and curbs | raised sidewalks along streets | `Do task A3 from docs/ROADMAP.md.` |
| 11 | A1 Roof life | low walls around flat roofs, stair rooms | `Do task A1 from docs/ROADMAP.md.` |
| 12 | A9 Lit windows by household | a believable mix of lit windows at night | `Do task A9 from docs/ROADMAP.md.` |
| 13 | Q4 Blender 5 haze | warmer, hazier Blender 5 beauty renders | `Do task Q4 from docs/ROADMAP.md.` |
| 14 | B1 Rivers and lakes | rivers, lakes and bridges (use `/effort high`) | `Do task B1 from docs/ROADMAP.md.` |
| 15 | B2 Farmland and olive groves | fields and olive rows around villages | `Do task B2 from docs/ROADMAP.md.` |
| 16 | C3 Godot 4 starter | walk the city in Godot (use `/effort high`) | `Do task C3 from docs/ROADMAP.md.` |
| 17 | D1 Richer gazetteer | district histories and families for stories | `Do task D1 from docs/ROADMAP.md.` |
| 18 | D5 Names in Arabic and Latin | every name in both scripts | `Do task D5 from docs/ROADMAP.md.` |
| 19 | Q5 Lighter old-town tiles | same look, smaller files | `Do tasks Q5 and C2 from docs/ROADMAP.md.` |

## Big tasks (H1, H2, and any task marked L): plan first, then small steps

Session 1, a stronger model only for the plan:
```
/model opus
/effort medium
```
```
Plan task H1 from docs/ROADMAP.md. Write the design into docs/SPEC.md and split H1 into small tasks (H1a, H1b, ...) in docs/ROADMAP.md, each doable in one Sonnet session. Do not write code.
```
Then one new session per small task, back on the normal settings:
```
Do task H1a from docs/ROADMAP.md.
```
(Same for H2: replace H1 by H2.)

## Useful extra prompts

- Very cheap health check (uses a Haiku helper):
  `Use the city-checker agent to check the repo.`
- Something looks wrong (attach a screenshot if you can):
  `In the souk view, the awnings float above the shops. Fix it with the smallest change.`
- Save the work to GitHub: `Commit and push.`
- Update the 3D page for your phone:
  `Rebuild the 3D page: run a quick build, then .venv/bin/python tools/make_artifact.py output/bodjantouna-42 /tmp/city-page, and publish that folder to https://claude.ai/artifact/HMtdFZUV9sGmyPn4q8mKsq (index.html plus every file under data/).`
- Claude goes round in circles (same error more than twice): press Esc, type `/model opus`,
  say `Fix only this problem.`, then go back to `/model sonnet`.
