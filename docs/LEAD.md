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
- The 5-hour limit cuts running helpers off mid-work when it reaches 100% (Ali, 3 November): while
  helpers run, check `get_usage` about every 30 minutes (a background `sleep 1800` wakes the lead); at
  about 80% with more than half an hour to its reset, have each helper save its state and report, then
  resume it after the reset with SendMessage; start new helpers right after a reset, never just before
  one. Measured on 3 November: the account (three Opus helpers, the lead and Ali's own other sessions,
  which share the limits) used about 27% of the window per hour; steer by the live percentages.
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
   - Run the tests and `build --quick`; `git diff HEAD | grep -c $'\u2014'` must print 0 (plain
     `git diff` misses staged changes, for example after `git cherry-pick -n`).
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
  nothing. Heights vary a lot: the quick cemetery climbs from about 1 m to 70 m.
- **Fair looks.** Every version from the same cameras: `tools/snapshot.py <build folder> --png F --view
  aerial --width 960 --height 720 --query "cam=...&look=...&ui=0"` (sandbox off), then a side-by-side
  sheet with PIL. A helper's own pictures use its own camera, so two helpers' pictures cannot be
  compared. Prompt 101 turns this into a tool.
- **Other seeds while a helper edits** (CP4): build them from a clean copy of the commit
  (`git worktree add --detach "$TMPDIR/head" HEAD`, then run the main `.venv/bin/python` there with
  `--out` pointing back into `output/`), so half-made edits never mix in; the same copy builds a HEAD
  quick city to count instances against. Look at new camera views in the GPU viewer: the seed 7
  cathedral view first stood against a wall, then inside a tree crown, both invisible in the numbers.
- **Survey the whole city, not the fixture** (prompt 46): a helper's tests can all pass while the
  program is wrong. A 20-line script over every house of the quick capital (rooms per type, sizes,
  what is missing) found 61 compact houses without a kitchen and 30 m2 washrooms that `rooms.check`
  never looked at. Write it while the helper works, and send the numbers back with examples.
- **Check a helper's root cause before deciding a rule** (prompt 47): the helper blamed missing chambres on
  the flat-type thresholds and asked for a rule change; an area histogram of the failing flats showed the
  main cause was slivers of 0-20 m2 counted as flats (a split bug). Set the bar as a pass rate per group
  (95% of each group passing `rooms.check`, as the old town reached), run `tools/interior_survey.py` after
  each round, and send the counts by kind with two plan pictures. Five rounds took villas and maisons to
  96%, slabs to 93%, colonial blocks only to 39% (open item 47.1).
- **A helper cut off by an error** (a network drop): `git diff` to see where it stopped, then SendMessage
  to the same helper; it resumes with its context.
- **No browser pane** (prompt 50, a run without MCP tools): drive the real viewer with a Playwright script on
  Chrome (`snapshot._launch(pw, gpu=True)`, `start_server`, `_wait_ready`): click a grid of points on a view
  until the card shows what you test, catch new tabs with `context.expect_page()`, use `select_option` for
  menus and mouse drags to orbit, and print the card's text after each click.
- **Blind, exact reruns.** To rerun a prompt, take its exact text from the transcript and compare its
  sha1; hide anything that would leak the answer (a memory note) while it runs, and restore it after.
- **Scoring.** Declare criteria and weights before judging (the duel: result 30, solid work 25,
  thinking 15, efficiency 15, code 10, cost in the city 5), score with evidence, and say what the total
  hides (Opus max won on care, Opus high on looks and value).
- **Take a number down to its causes.** "36 km of river deep under the ground" was accepted as a price until a list of every
  stretch with what lay at its low point showed one cause, pockets of salt basins, and a two-line idea removed it all.
  Ask of every number the helper calls a price: which single cause makes most of it?
- **The street graph of every settlement:** `tools/street_survey.py` (`--quick`, or the 64 km world in about 10 minutes):
  the settlements of more than one part and the bar of 99.5%. Run it after any step that moves villages.
- **Judge interiors on more than one plan.** Rounds of fixes won the bars house by house on one capital; a fresh deal of the same
  city fell by 3-5 points in four groups (names-60). A rate on one plan is partly memory of that plan: run the survey on the
  capital, `--city villas` and a world of another seed, and never fix one house for its own sake.
- **Order work by what it moves.** Before tuning anything on a plan, list the open prompts whose fingerprint allows `plan/*`
  (a Python loop over docs/prompts and the ROADMAP's ticks does it) and do those first.
- **Reviewers by lens, a probe for every finding** (valleys, 5 November). Three Opus reviewers at high effort on a clean copy (ground and water; the plan; what was not updated, and the rules), told to read the code, not the author's notes, given the known limits, and asked only for what they ran. Under 1% of the week, and they found what every gate had passed: the quay bug. Scale a finding at full size before deciding: a 4 m fault on quick seed 11 was 0.35 m on Ali's world and 2.45 m on seed 7.
- **Waiting costs nothing.** Long gates in a background script use no tokens: seven worlds of surveys, the slow tests and the 64 km gates cost less than the reviewers. A survey of all groups takes 20 minutes because of colonials and slabs: `--groups dar,compact,small,shop` for the many worlds, all groups on the capital.
- **A reviewer's probe may import its own copy.** A crack looked unfixed because the probe's `common.py` held `sys.path.insert(0, <old copy>)`: read its first lines before rerunning it on a fix.
- **After any fix that moves a plan, run the slow tests again:** two fast and one slow test broke on the new deal, and all three were the tests' own reading (a point along a wall, a wall back to back), not the plan. Read the failing case before touching the bar or the code.
- **A cause is proved by taking one thing out.** Facades read a test failure as door-windows in baths; on the merged code none of
  the failing rooms had one, and `gable_windows = 0` passed. Ask for that one run before repeating a cause to Ali.

- **Measure before you brief** (prompt 62). A 30-line probe over the crossings found what shaped the design: quays 0-0.7 m over the water, oblique lines of 150 m on a stream 3 m wide, one crossing in 1.7 km of the capital's river. The brief states the numbers and the decisions, so the helper builds instead of discovering.
- **A fresh helper per round** (prompt 62). Plan and heights, structure, fixes: three Opus helpers in turn, about 1% of the week each, all reading one brief file in `docs/wip/`. A fresh helper with a narrow section costs far less than one long context, and its record-only interface is reviewed in between.
- **Reviewers from a frozen copy, before the commit.** `cp -R citygen styles tools tests` to the scratchpad, two reviewers by lens, the gates running beside them in one background script (no tokens). Under 1% of the week for both, and they found what 283 tests and every gate had passed, the worst visible in one picture. Ask for each finding's probe, and rerun the gates after the fixes.
- **A check over every triangle.** Flips, NaN, feet, overlaps over all bridges of a 64 km world take minutes of machine time and no tokens, and a reviewer's check of that kind found what eight pictures had not.
- **Scans of many seeds cost little.** `TileContext(world, [])` lists a seed's road decks in about a minute: 13 seeds showed what three worlds could not. Boxes rebuild a place in 10-100 s, a country box in 8 s, so eye-height work on one bridge is cheap; take a camera from the record, never a guess.

- **Look at the longest and the oddest first** (prompt 62, round 4). The worst fault of that round, a dark band 1 m over the grass under long decks, was in no bar and no test.
- **A reviewer after every round that adds code.** Rounds 4 and 5: 810 new lines passed 301 tests; a third reviewer still proved a fault on every skew bridge. A fix round is cheap, about 0.5% of the week on a fresh helper.
- **Name the slow tests in the brief.** A helper told "the lead runs the slow tests" left one failing that its own change broke on purpose: give it the slow tests that read what it touches.

## 4. Gotchas on Ali's Mac

More in the auto-memory note on the Mac environment.
- `.venv/bin/python`, never `python`. Tests about 70 s (`-m slow` about 5 minutes), `build --quick` about 13 s, the full capital
  about 60 s.
- Snapshots, before/after pictures, the gallery and the phone-page preview start local web servers: run
  them with the sandbox off. `open` and `osascript` are blocked inside the sandbox: give Ali the
  command instead.
- Playwright's cached Chromium vanished on 29 October; since commit 19cc596 `tools/snapshot.py` falls
  back to the installed Google Chrome (`channel="chrome"`, one line on stderr says so). Never run
  `playwright install` (about 250 MB) without Ali's yes.
- The gallery: `Open City Gallery.command` or `.venv/bin/python -m citygen gallery` (port 8765, or a
  free one). If Ali sees "localhost refused to connect", it is not running: start it for him in the
  app's Terminal panel (`run_in_terminal`), where it keeps running after your turn.
- Blender starts only through `tools/make_blend.py` or `tools/blender_kit_export.py`, each typed exactly
  as a command of its own. The Blender route of prompt 38 is tested but has carried no city asset yet
  (the kit: 185 pieces made by code, 58 from the Tounes kit).
- A `cd` into a worktree moves the session's working directory for the next commands: use absolute
  paths or a subshell `( cd ... && ... )`.
- Helpers share the lead's session scratchpad folder: start the names of your own scripts there with
  `lead` (prompt 47: the lead's `survey47.py` overwrote the helper's script of the same name).
- Helpers in their own worktree (`isolation: "worktree"`) start without `output/` and `.venv`: tell them
  to run `/Users/mohamedalimabrouki/Desktop/City/.venv/bin/python` from their own folder.
- Tool inputs turn a backslash-u escape into the real character: never type the em dash's escape in
  Write or Edit content (it lands as the forbidden character); in scripts build it with `chr(0x2014)`,
  and check with `git grep -c "$(printf '\342\200\224')"` before every commit.
- The phone page lives at https://claude.ai/artifact/HMtdFZUV9sGmyPn4q8mKsq: read it with the Artifact
  tool before publishing to it; 16 MB per file, 64 MB per publish. The built-in browser is not signed in
  to Claude, so it cannot show the live page: check a host-like local copy (HANDOFF, "Phone page").
- macOS `ls -l` shows extended attributes: do not parse its columns.
- Ali's API credit (30 October): his Console credit is promotional ($100 granted 11 October, expires 14
  November) and pays for the API and the Agent SDK, not Claude Code; anything started inside the Claude
  app (chat, "!" box, Terminal tabs) uses his Max plan. To spend the credit, run a prompt with
  `.venv-sdk/bin/python tools/run_on_credit.py "Do prompt N."` outside the sandbox (a Terminal tab): the
  same lead (Opus, high effort, this folder's settings) runs through the Agent SDK on the Console key
  that `claude auth login --console` saved, and `--resume "..."` answers it. Its session file lands in
  `~/.claude/projects/` like any other, for review. Without a chat window Claude stops background
  helpers 10 minutes after the lead's turn ends (prompt 48's first helper died so, unnoticed by its
  lead): the launcher sets `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` to wait for them.
  The credit ran out on 31 October: the chain run (`.venv-sdk/credit_chain.sh`) stopped at 13:12 with
  "Credit balance is too low", so this route needs new credit first (checked 3 November).

## 5. Where the decisions are

- Accepted budget overshoots and relaxed targets (light tiles, the 3.5 MB tile target, kiosk cafés,
  arterials without street trees): the CP4 list in the WORKLOG "Resume here" entry.
- Lessons by topic: `docs/HANDOFF.md`, "Decisions and lessons".
- The model duel and the two tracks (25 October): the WORKLOG entries of that day and HANDOFF "Where
  things stand".
