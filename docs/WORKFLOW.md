# Working with Claude cheaply

## The big idea

Claude never builds the world by hand. Claude only improves the **generator** (the program),
and the generator builds the world for free on your computer. A bigger world costs computer
time, not tokens. So the goal of every session is one small, tested improvement to the code.

## Your routine for each task

1. Open Claude Code in this folder.
2. Set the model and effort shown for the next prompt in `docs/PROMPTS.md`.
3. Give the prompt by its number, for example:
   `Do prompt 12.`
   That is the whole prompt. The prompt text in `docs/prompts/`, `CLAUDE.md` and `docs/SPEC.md`
   tell Claude what to read, how to check, and how to commit.
4. Look at the result yourself: `python -m citygen build --quick`, then `python -m citygen view`
   (or open the PNG maps in `output/.../maps/`).
5. Happy: keep it (Claude has already committed). Not happy: say what looks wrong in one or two
   sentences, in the same session.
6. Type `/clear` before the next task. A fresh conversation is cheaper than a long one.

## Which model for what

| Job | Model and effort |
|---|---|
| Run the checks, rename things, small text edits | Haiku (`/model haiku`) |
| A normal roadmap task | Sonnet, medium (the default) |
| A big task marked "Sonnet high" or "Opus low" | Sonnet `/effort high`, or Opus `/effort low` |
| A bug Sonnet failed twice, or a new big design | Opus, medium |
| Rethinking the whole architecture | Opus, high (rare) |

## Ten ways to spend less

1. One task per session, then `/clear`.
2. Small tasks. If a task feels big, ask Claude to split it in the roadmap first (cheap), then do
   the parts one by one.
3. Never paste or attach generated files (`.glb`, `plan.json`, `world.json`). They are huge.
   Claude reads `python -m citygen stats` and the PNG maps instead.
4. Use `--quick` builds while developing. Build the big world only when a feature is done.
5. Do not ask "improve everything" or "make it better". Name the one thing you want.
6. If Claude is going round in circles on the same error (more than two tries), stop it with
   Esc and switch to a stronger model for that one problem, then switch back.
7. Keep `CLAUDE.md` short. It is read in every session, so every extra line costs every time.
8. Screenshots help Claude understand visual problems faster than long descriptions.
9. Let the tests do the checking. A failing test tells Claude exactly what is wrong.
10. Describe what you see, not how to fix it. Claude reads the code to find the fix.

## Ultracode, honestly

**What it is:** a Claude Code mode where Claude writes a small "workflow" program that launches
many helper agents at the same time (for example, four agents each building one part, then
others checking them).

**When it is worth it:** jobs that split into independent parts, like several roadmap tasks that
touch different files, or a full review of the generator. It is faster, but it is never cheaper
than one Sonnet session, because every helper agent costs tokens.

**How to switch it on (at the time of writing):**
- for one prompt only: put the word `ultracode` in your message;
- for the whole session: `/effort ultracode`, and `/effort ultracode off` to stop.
It needs workflows to be available on your plan.

**How to keep it cheap:**
- This repository already makes helper agents use **Sonnet by default** (the setting
  `CLAUDE_CODE_SUBAGENT_MODEL` in `.claude/settings.json`).
- In `/config`, set **Dynamic workflow size** to **small** (fewer than 5 agents per run).
- Give it a precise job: `ultracode: do tasks A1, A7 and B6 from docs/ROADMAP.md in parallel,
  each by one agent, then run the tests once.`

## Already set up in this repository

- `CLAUDE.md`: short rules every Claude session follows (what to read, how to test, how to commit).
- `.claude/settings.json`: helper agents default to Sonnet, and running the tests and the
  generator does not ask for permission each time.
- `.claude/agents/city-builder.md`: a Sonnet helper that does one roadmap task.
- `.claude/agents/city-checker.md`: a Haiku helper that runs the tests and a quick build and
  reports. Very cheap. Ask: `Use the city-checker agent to check the repo.`
- "Manager and worker" option: keep the main session on Opus at low effort and say
  `Use the city-builder agent to do task B2.` Opus plans and reviews, Sonnet does the typing.

## Copy-paste prompts

The full list, 100 prompts in order with model and effort, is in `docs/PROMPTS.md`.

- `Do prompt 4.`
- `Use the city-checker agent to check the repo.`
- `The medina alleys look too straight in output/.../maps/<city>.png. Make them more winding. Keep the change small.`
- `Split task B1 in docs/ROADMAP.md into three smaller tasks. Do not write code.`
- `Build seed 7 with python -m citygen build --seed 7 --quick and tell me the capital's name and stats.`
