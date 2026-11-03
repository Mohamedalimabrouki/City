# rev-lead-notes: review of docs/LEAD.md against CLAUDE.md (3 November, 4-minute pass)

Most lessons are right and match CLAUDE.md (baseline, fingerprint, make_blend, Blender rule, `.venv/bin/python`, timings, em dash rule). Findings:

| # | Where | Severity | Problem | One-line fix |
|---|-------|----------|---------|--------------|
| 1 | docs/LEAD.md:57 with :77 | high | After `git cherry-pick -n` the changes are staged, so plain `git diff` is empty: the em dash check prints 0 and "read the whole diff" shows nothing. It also never sees untracked new files. | Use `git diff HEAD` (or `--cached`) for the review and the em dash count; `git add -N` new files first. |
| 2 | docs/LEAD.md:74-76 vs CLAUDE.md "Check your work" and "Finish" | medium | CLAUDE.md tells every session (helpers too) to tick ROADMAP, write WORKLOG and HANDOFF, and write questions in WORKLOG when stuck; LEAD.md says worktree helpers never touch them, but helpers do not read LEAD.md (:4). | Add one line to CLAUDE.md: "a helper in its own worktree writes only docs/wip/<name>.md; the lead moves it into the shared docs" (or always put it in the brief). |
| 3 | docs/LEAD.md:50 vs :82 | low | Step 3 says the helper does not commit; step 8 says it commits on its branch. Both are right for their mode but read as a conflict. | Say "single helper on this folder: do not commit; helper in a worktree: commit on its own branch". |
| 4 | docs/LEAD.md:29-31 | medium | At the measured 27-37% per hour, a check every 30 minutes can jump from below 80% to near 100% between two checks. | Check every 15 minutes once above 60%. |
| 5 | docs/LEAD.md:71 | low | Worktrees under /tmp are lost at a reboot (macOS cleans /tmp), with any unpushed work; stale entries stay in .git/worktrees. | Add: push wip/<name> early; after a reboot run `git worktree prune`. |
| 6 | docs/LEAD.md:77 | low | `git cherry-pick -n <commit>` takes one commit; a wip branch with several commits loses the others. | Use `git cherry-pick -n main..wip/<name>` or `git merge --squash`. |
| 7 | docs/LEAD.md:158 vs :57 | low | `git grep -c` prints nothing (not 0) when clean, unlike line 57's "must print 0". | Say "must print nothing", or use one check in both places. |
| 8 | docs/LEAD.md:12 vs CLAUDE.md "reports under 10 lines" | low | "a checkpoint under 15" is an exception CLAUDE.md does not have. | Add the checkpoint exception to CLAUDE.md, or drop it here. |
| 9 | docs/LEAD.md:59, :102 vs CLAUDE.md "at most two snapshots per task" | low | Lead's same-camera comparisons can exceed two snapshots. | Say the lead's review views are separate from the helper's two, or keep within two. |
| 10 | docs/LEAD.md:163-174 | low | The API credit route is closed (credit ran out 31 October, expires 14 November): 12 lines of stale detail. | Cut to two lines: "route exists, needs new credit; see HANDOFF". |

Left (not done in 4 minutes): not checked whether `SendUserFile` (:16) and `get_usage` (:23) exist in every session; did not verify the claim that the sandbox refuses `git worktree add` in .claude/worktrees (:72).
