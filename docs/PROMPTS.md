# The playbook: 100 prompts

From here the project grows through 100 small tasks (plus 20.1 and 20.2, added after review),
one per session, in this order. Each row below names the model and effort to use. The full text
of every prompt is in `docs/prompts/`; Claude reads it there, so you only type the number.

## How to run one prompt

1. Start a new session in the City folder (or type `/clear` in the current one).
2. Set the model and effort from the table: the model menu in the app, or type for example
   `/model sonnet` and then `/effort high`.
3. Type: `Do prompt 7.` That is the whole prompt.
4. The session reports in under 10 lines and tells you what to look at: usually a before/after
   picture in `output/checks/`, sometimes the viewer (`.venv/bin/python -m citygen view`).
   If something looks wrong, say it in one or two sentences in the same session.
5. For the next prompt, start a new session again. A fresh session costs less than a long one.

## Good to know

- **Order.** Follow the numbers (20.1 and 20.2 come after 20). "Needs" lists the prompts that
  must be done first; a session checks this itself and stops if something is missing.
- **Checkpoints (CP).** Nine review prompts on Opus. They check the last 10 to 15 tasks and fix
  small problems before they pile up. Do not skip them: they are what keeps the quality
  world-class while you work without me. If a checkpoint adds a fix prompt (for example
  `16.1`), run it before the next number.
- **Pictures.** The picture tool starts a small local web server, which Claude's sandbox
  blocks. When a session asks to run it outside the sandbox, say yes. To stop being asked,
  set `sandbox.network.allowLocalBinding` to `true` in your Claude Code settings.
- **Blender.** After every prompt that changes the city, the session refreshes
  `output/bodjantouna-42/goumosbane.blend`: double-click it to see the progress (golden-hour
  scene with a camera per view: street, aerial, souk, and new views as prompts add them). To
  refresh it yourself: `.venv/bin/python tools/make_blend.py`.
- **Other models (DeepSeek in OpenCode).** From prompt 7, a trial runs the build prompts with
  DeepSeek V4.1 Flash in OpenCode (free). OpenCode reads `CLAUDE.md` by itself, so type the same
  `Do prompt 7.` there; do not add an `AGENTS.md` file (OpenCode would read it instead of
  `CLAUDE.md`). Keep these on Claude: the checkpoints (6, 16, 27, 43, 58, 69, 78, 91, 100), the
  big designs (44, 51, 94, 98) and the phone page (42, 99: they need Claude's Artifact tool).
  Never run two agents on this folder at the same time. Checkpoint 16 judges the trial; the
  backup point before it is the git tag `before-deepseek`.
- **Engines.** Godot and Unreal are not on your Mac. Prompts 72-75 ask you before installing
  anything; you can also postpone them.
- **Stuck session.** If it repeats the same error more than twice, stop it (Esc), switch to
  Opus, say `Fix only this problem.`, then switch back.
- **Can wait.** Prompts 72-78 (game engines and Tounes Rush) and 92-98 (scale and new styles)
  can be postponed; 70 and 71 cannot, because the stories need them. Prompts 99 and 100 adapt
  to what is done.
- **The end.** After prompt 100, come back to your lead session and say so: it checks
  everything using `docs/WORKLOG.md` and `docs/REVIEW.md`.

## What the settings mean

| Setting | Use |
|---|---|
| Sonnet, low | tiny chores |
| Sonnet, medium | normal tasks |
| Sonnet, high | harder code: geometry, performance, new file formats |
| Opus, medium | checkpoints and medium designs |
| Opus, high | the big designs (interiors, two-level city) and the final review |

## The prompts

| # | Task | Model | Effort | Needs | You look at |
|---|---|---|---|---|---|
| 1 | T1 Regression fingerprint tool | Sonnet | medium | - | - |
| 2 | T2 Before/after pictures | Sonnet | medium | 1 | a test picture |
| 3 | T3 Housekeeping | Sonnet | low | 1 | - |
| 4 | C1a Build tiles in parallel | Sonnet | high | 1 | - |
| 5 | C1b Resumable builds | Sonnet | high | 4 | - |
| 6 | CP1 Checkpoint: foundations | Opus | medium | 1-5 | the report |
| 7 | Q3 Bougainvillea that cascades | Sonnet | medium | 2 | kit sheet |
| 8 | V1 Golden hour in the viewer | Sonnet | high | 2 | street |
| 9 | V2 Ambient occlusion | Sonnet | high | 8 | street |
| 10 | Q4 Blender 5 haze | Sonnet | high | 1 | Blender render |
| 11 | A4a City ground | Sonnet | high | 2 | street |
| 12 | A4b Everything on the graded ground | Sonnet | high | 11 | souk |
| 13 | A3 Sidewalks and curbs | Sonnet | high | 12 | street |
| 14 | S1 Street surfaces and markings | Sonnet | medium | 13 | street |
| 15 | A1 Roof life | Sonnet | medium | 2 | close aerial |
| 16 | CP2 Checkpoint: light and ground | Opus | medium | 7-15 | the report |
| 17 | A2a Textures in the 3D files | Sonnet | high | 1 | - |
| 18 | A2b Generated textures | Sonnet | high | 17 | texture sheet |
| 19 | A2c Textured walls and roofs | Sonnet | high | 18 | street |
| 20 | A2d Ground textures | Sonnet | medium | 19 | street |
| 20.1 | AD1 Every home gets a door and windows | Sonnet | high | 13 | modern estate |
| 20.2 | AD2 Impasses to landlocked houses | Sonnet | high | 20.1 | souk |
| 21 | A9 Lit windows by household | Sonnet | medium | 8, 20.1 | street at night |
| 22 | AR1 Arcades and iron balconies | Sonnet | high | 13 | street |
| 23 | AR2 Building massing | Sonnet | high | 15 | close aerial |
| 24 | A7 More greenery | Sonnet | medium | 13 | aerial |
| 25 | H3a Parked cars and taxis | Sonnet | medium | 13 | street |
| 26 | H3b Benches, kiosks, fountains | Sonnet | medium | 13 | street |
| 27 | CP3 Checkpoint: facades and street life | Opus | medium | 17-26 | the report |
| 28 | P1 People figures | Sonnet | high | 2 | kit sheet |
| 29 | P2 People in the streets | Sonnet | medium | 28, 13 | souk |
| 30 | A5a The kasbah | Sonnet | high | 12 | aerial |
| 31 | A5b Covered souks | Sonnet | high | 2 | souk |
| 32 | A5c Cathedral and theatre | Sonnet | high | 22 | street |
| 33 | A5d Station and clock tower | Sonnet | medium | 1 | aerial |
| 34 | A6a Quays, breakwater, lighthouse | Sonnet | high | 12 | port |
| 35 | A6b Boats and cranes | Sonnet | medium | 34 | port |
| 36 | A6c Corniche promenade and beach | Sonnet | medium | 34, 13 | corniche |
| 37 | H3c Seaside cafes | Sonnet | medium | 36, 29 | corniche |
| 38 | A8 Blender kit export | Sonnet | medium | 1 | - |
| 39 | Q5 Lighter tiles | Sonnet | high | 1 | souk |
| 40 | C2a Level-of-detail tiles | Sonnet | high | 39 | - |
| 41 | C2b Viewer level of detail | Sonnet | high | 40, 4 | aerial |
| 42 | R1 Refresh the phone 3D page | Sonnet | medium | 41 | your phone |
| 43 | CP4 Checkpoint: people, landmarks, port | Opus | medium | 28-42 | the report |
| 44 | H1 Interiors: the design | Opus | high | 15, 20.2 | the summary |
| 45 | H1a Interior model and command | Sonnet | high | 44 | - |
| 46 | H1b Courtyard houses | Sonnet | high | 45 | house plans |
| 47 | H1c Apartments, villas, shops | Sonnet | high | 46 | house plans |
| 48 | H1d Interior walls and openings | Sonnet | high | 47 | interior |
| 49 | H1e Floors, stairs, roof terrace | Sonnet | high | 48 | interior |
| 50 | H1f Interiors in the viewer | Sonnet | high | 49 | interior |
| 51 | H2 Furnishing: the design | Opus | medium | 50 | the summary |
| 52 | H2a Traditional furniture | Sonnet | high | 51 | kit sheet |
| 53 | H2b Modern furniture | Sonnet | medium | 51 | kit sheet |
| 54 | H2c Furnishing rules | Sonnet | high | 52, 53 | interior |
| 55 | H2d Light, textiles, clutter | Sonnet | medium | 54 | interior at night |
| 56 | H4a Hero scenes | Sonnet | high | 55 | the scene |
| 57 | H4b Hero scenes in Blender | Sonnet | high | 56, 10 | Blender render |
| 58 | CP5 Checkpoint: interiors | Opus | medium | 44-57 | the report |
| 59 | B1a Rivers | Sonnet | high | 1 | country map |
| 60 | B1b Valleys, lakes and water | Sonnet | high | 59 | aerial |
| 61 | B1c Rivers in towns | Sonnet | high | 60 | aerial |
| 62 | B1d Bridges | Sonnet | medium | 61 | aerial |
| 63 | B2a Fields and cactus hedges | Sonnet | high | 60 | aerial |
| 64 | B2b Olive groves and orchards | Sonnet | medium | 63 | aerial |
| 65 | B3 Salt lakes and dunes | Sonnet | high | 60 | aerial |
| 66 | B4 Oasis towns | Sonnet | high | 1 | aerial |
| 67 | B5 Hilltop ksar villages | Sonnet | high | 12 | aerial |
| 68 | B6 Regions and natural names | Sonnet | medium | 59, 65 | country map |
| 69 | CP6 Checkpoint: countryside | Opus | medium | 59-68 | the report |
| 70 | C4a Street graph for games | Sonnet | medium | 12 | - |
| 71 | C4b Building entrances | Sonnet | medium | 70, 20.2 | - |
| 72 | C3a Godot: stream the city | Sonnet | high | 40 | Godot |
| 73 | C3b Godot: walk the streets | Sonnet | high | 72 | Godot |
| 74 | C3c Godot: sky, night, guide | Sonnet | medium | 73 | Godot |
| 75 | C5 Unreal 5 import | Sonnet | high | 39 | Unreal |
| 76 | C6a Tounes Rush city runs | Sonnet | high | 70 | the game |
| 77 | C6b Country map unlocks | Sonnet | medium | 76 | the game |
| 78 | CP7 Checkpoint: game-ready | Opus | medium | 70-77 | the report |
| 79 | D7 Street names and addresses | Sonnet | medium | 71 | a sample |
| 80 | D6 Residents | Sonnet | medium | - | a sample |
| 81 | D1a District histories | Sonnet | medium | 1 | a sample |
| 82 | D1b Notable families and guilds | Sonnet | medium | 80 | a sample |
| 83 | D1c Local legends | Sonnet | medium | 81 | a sample |
| 84 | D3 Canon for everything | Sonnet | medium | 81 | a sample |
| 85 | D4a Timeline | Sonnet | high | 81 | a sample |
| 86 | D4b Factions | Sonnet | medium | 85 | a sample |
| 87 | D5a Arabic place names | Sonnet | high | 1 | 30 names |
| 88 | D5b Arabic people and street names | Sonnet | high | 87, 79 | 30 names |
| 89 | D2a Country poster map | Sonnet | high | 87, 68 | the poster |
| 90 | D2b City poster map | Sonnet | high | 89, 79 | the poster |
| 91 | CP8 Checkpoint: stories | Opus | medium | 79-90 | the report |
| 92 | E2 Faster terrain | Sonnet | high | 1 | - |
| 93 | E1 Whole-country builds | Sonnet | high | 5, 41, 92 | aerial |
| 94 | F4 Styles per region | Opus | medium | 1 | aerial |
| 95 | F2 Medieval fantasy town | Sonnet | high | 94 | aerial |
| 96 | F1a Steampunk style pack | Sonnet | high | 94 | street |
| 97 | F1b Steampunk machines | Sonnet | high | 96, 62 | aerial |
| 98 | F3 Two-level city: the design | Opus | high | 94 | the summary |
| 99 | G1 Gallery, guide and phone page | Sonnet | medium | 57, 42 | the gallery |
| 100 | CP9 Final review | Opus | high | 1-91, 99 | the review |
