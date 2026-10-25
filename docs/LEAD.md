# The lead's handbook

For the lead session: the Claude session Ali talks to, which has run the playbook since prompt 20
(one helper per prompt, reviewed by the lead before it commits). Helpers do not need it. Read it with
`CLAUDE.md` and the "Resume here" entry at the top of `docs/WORKLOG.md`; the project's lessons are in
`docs/HANDOFF.md`. Ali asked (25 October 2026) that every new session work with the same knowledge
and care as the last one: keep this file up to date when you learn something that would help.

## 1. Ali

- Mechatronics engineer who does 3D in Blender (his character Léo is his quality bar), video and
  stories; not a developer. Plain B2 English, define jargon, reports under 10 lines (a checkpoint under
  15), step by step when he sends screenshots. Never the em dash character.
- He wants world-class work and honest verdicts ("complete, extremely wonderful work, impress me").
  Never lower the bar to finish; say plainly what is not done or not verified.
- He follows from his phone, often in a café: send the best picture of each step with SendUserFile as
  soon as it exists.
- "Just answer, don't build" means: answer only, change nothing.
- He likes experiments judged fairly (the model duel): declare criteria and weights first, verify every
  claim yourself, compare under identical conditions, then give a clear winner and the trade-offs.
- Keep what he says to keep: the three experiment worktrees in `.claude/worktrees/` stay until he says
  otherwise.
- His weekly limit matters. The app's usage tool (`get_usage`) gives the 5-hour and weekly percentages
  and the reset time (Tuesdays about 21:00 UTC). What is unused at the reset is lost: before it, suggest
  the best use of what is left; plan heavy work (checkpoints) for the start of a week. A long session
  costs more per message, so one fresh session per prompt (or small batch) is cheaper: this file exists
  so a fresh session loses nothing.
- Where he wants to go: the 100 prompts, then two tracks (prompts 101-120,
  `docs/prompts/10-life-and-polish.md`): every asset polished to hero quality, and a city with life.

## 2. Running a prompt in lead mode

1. "Do prompt N" or "continue the playbook": read the `## N.` section in `docs/prompts/*.md` and check
   that its Needs are ticked in `docs/ROADMAP.md`.
2. Baseline: `.venv/bin/python -m citygen build --quick`, then `.venv/bin/python tools/fingerprint.py
   save before`.
3. Brief one `city-builder` helper (Agent tool); one helper at a time on this folder. The playbook table
   gives the floor for model and effort; Opus at high effort when looks matter (the duel's lesson),
   Sonnet for routine code, max only for hard or risky work (it buys care, not looks, at about twice the
   cost). The brief: read CLAUDE.md, the prompt section and the HANDOFF lessons it touches; what "done
   well" means for this prompt; the environment facts of section 4; the routine (tests, build,
   fingerprint compare with the prompt's allow list, pictures, docs, WORKLOG entry); do not commit;
   report in under 250 words (what and why, numbers before and after, tests, fingerprint, picture
   paths, an honest self-assessment). Small prompts, or ones that need your own tools (the Artifact
   tool for the phone page), you do yourself.
4. Review it yourself: the report is a claim, not proof.
   - Read the whole diff: the style of nearby code, numbers in the style files, a stream of its own for
     every new choice, no new draws on an old stream, small functions.
   - Run the tests and `build --quick`; `git diff | grep -c $'\u2014'` must print 0.
   - Fingerprint: explain every changed part down to its cause (section 3), not just "expected".
   - Look at the pictures yourself. For looks, compare versions from the same cameras. Night glass and
     things near the sea need the GPU browser pane: headless snapshots draw them wrong.
   - Send follow-ups to the same helper (SendMessage) until it is right.
5. Tiles changed: refresh Blender with exactly `.venv/bin/python tools/make_blend.py` (a command of
   its own) and name the .blend in the report.
6. Finish: a WORKLOG entry (while the work is paused, the "Resume here" entry stays first and newer
   entries go just below it), HANDOFF lessons, the ROADMAP tick, commit only the files you changed (one
   commit per prompt, ending with the Co-Authored-By line the app gives), push, then report to Ali with
   the picture.
7. Checkpoints add an independent Opus reviewer that reads only the committed history with git (it can
   run beside a builder), then a fix round; CP3 also ran a speed round with byte-identical output.

## 3. Review techniques that worked

- **What changed inside a tile.** A GLB tile is a JSON chunk and a binary chunk. Read the JSON and, for
  every node with `EXT_mesh_gpu_instancing`, count the instances (the `TRANSLATION` accessor's `count`)
  per mesh name; compare with the same tile of the main build. This showed that the cypress's 227 extra
  triangles in tile 12_22 were 3 walkers changing costume: the crowd's byte budget is `bytes_share`
  (8.5%) of the tile's size, so a bigger tile lets one more costume figure fit. Expected, not a stream
  bug.
- **Heights for cameras.** `?cam=x,y,z` takes absolute heights (meters). Take the ground from
  `Ground.surface`, or from the instance positions in a tile (decode the `TRANSLATION` accessor and
  apply the node transforms: glTF y is the height). Never guess: a camera under the ground draws
  nothing. The cemetery ground is about 15 m.
- **Fair looks.** Every version from the same cameras: `tools/snapshot.py <build folder> --png F --view
  aerial --width 960 --height 720 --query "cam=...&look=...&ui=0"` (sandbox off), then a side-by-side
  sheet with PIL. A helper's own pictures use its own camera, so two helpers' pictures cannot be
  compared. Prompt 101 turns this into a tool.
- **Blind, exact reruns.** To rerun a prompt, take its exact text from the transcript and compare its
  sha1; hide anything that would leak the answer (a memory note) while it runs, and restore it after.
- **Scoring.** Declare criteria and weights before judging (the duel: result 30, solid work 25,
  thinking 15, efficiency 15, code 10, cost in the city 5), score with evidence, and say what the total
  hides (Opus max won on care, Opus high on looks and value).

## 4. Gotchas on Ali's Mac

More in the auto-memory note on the Mac environment.
- `.venv/bin/python`, never `python`. Tests about 30 s, `build --quick` about 13 s, the full capital
  about 60 s.
- Snapshots, before/after pictures, the gallery and the phone-page preview start local web servers: run
  them with the sandbox off. `open` and `osascript` are blocked inside the sandbox: give Ali the
  command instead.
- The gallery: `Open City Gallery.command` or `.venv/bin/python -m citygen gallery` (port 8765, or a
  free one). If Ali sees "localhost refused to connect", it is not running: start it for him in the
  app's Terminal panel (`run_in_terminal`), where it keeps running after your turn.
- Blender starts only through `tools/make_blend.py` or `tools/blender_kit_export.py`, each typed exactly
  as a command of its own. The Blender route of prompt 38 is tested but has carried no city asset yet
  (the kit: 185 pieces made by code, 58 from the Tounes kit).
- A `cd` into a worktree moves the session's working directory for the next commands: use absolute
  paths or a subshell `( cd ... && ... )`.
- Helpers in their own worktree (`isolation: "worktree"`) start without `output/` and `.venv`: tell them
  to run `/Users/mohamedalimabrouki/Desktop/City/.venv/bin/python` from their own folder.
- Tool inputs turn a backslash-u escape into the real character: never type the em dash's escape in
  Write or Edit content (it lands as the forbidden character); in scripts build it with `chr(0x2014)`,
  and check with `git grep -c "$(printf '\342\200\224')"` before every commit.
- The phone page lives at https://claude.ai/artifact/HMtdFZUV9sGmyPn4q8mKsq: read it with the Artifact
  tool before publishing to it; 16 MB per file, 64 MB per publish.
- macOS `ls -l` shows extended attributes: do not parse its columns.

## 5. Where the decisions are

- Accepted budget overshoots and relaxed targets (light tiles, the 3.5 MB tile target, kiosk cafés,
  arterials without street trees): the CP4 list in the WORKLOG "Resume here" entry.
- Lessons by topic: `docs/HANDOFF.md`, "Decisions and lessons".
- The model duel and the two tracks (25 October): the WORKLOG entries of that day and HANDOFF "Where
  things stand".
