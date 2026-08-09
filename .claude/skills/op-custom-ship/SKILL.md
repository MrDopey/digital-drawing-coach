---
name: op-custom-ship
description: Implement, archive, and merge a Drawing Coach change into main. Use after /op-custom-propose when ready to ship.
license: MIT
disable-model-invocation: true
---

1. Before touching tasks, get the worktree clean: check `git status --porcelain`. If it's dirty (e.g. leftover spec changes from `/op-custom-propose`), commit them now so step 2's per-task commits start from a clean baseline:
   ```
   git add -A && git commit -m "chore: <change-name> — pre-apply spec changes\n\nCo-Authored-By: <model-name> <noreply@anthropic.com>"
   ```
   Skip if already clean.
2. Invoke `opsx:apply` with the change name — work through all tasks until complete. Once every task in a section is marked complete, commit that section's changes atomically before starting the next section:
   ```
   git add -A && git commit -m "feat: <change-name> — <section-summary> (section <n>)\n\nCo-Authored-By: <model-name> <noreply@anthropic.com>"
   ```
   Skip a section's commit only if it produced no file changes (e.g. a section of no-op verification tasks).
3. Invoke `opsx:archive` with the change name — sync delta specs and archive.
4. Commit any changes left in the worktree (archive sync output, stray files):
   ```
   git add -A && git commit -m "chore: <change-name> — archive\n\nCo-Authored-By: <model-name> <noreply@anthropic.com>"
   ```
   Skip if `git status --porcelain` is clean.
5. Stash any dirty changes on the shared checkout before merging:
   ```
   git -C <repo-root> stash
   ```
   Skip if `git -C <repo-root> status --porcelain` is clean.
6. Merge into main (repo root is two levels above `.claude/worktrees/<name>`):
   ```
   git -C <repo-root> merge <worktree-branch> --no-ff -m "Merge <branch>: <change-name>\n\nCo-Authored-By: <model-name> <noreply@anthropic.com>"
   ```
   Branch name: `git branch --show-current` inside the worktree.
7. Pop the stash if one was created in step 5:
   ```
   git -C <repo-root> stash pop
   ```
8. Check for orphaned `.openspec.yaml` on the shared checkout. If found, move it to the archive dir and commit the fix immediately.
9. Verify the merge landed, then remove the worktree:
   ```
   git -C <repo-root> merge-base --is-ancestor <worktree-branch> HEAD
   ```
   Exit 0 → call `ExitWorktree` with `action: "remove"`, `discard_changes: true` (the commit is preserved in `<repo-root>`'s history; no confirmation needed). Report the check result to the user.
   Non-zero → stop, `action: "keep"`, tell the user.

`<model-name>` = the display name of the model currently running this skill (e.g. "Claude Sonnet 5") — never hardcode a specific version.

**Guardrails:**
- Always use `--no-ff`.
- Do not merge before all tasks are complete and archive succeeds.
- Each section gets its own atomic commit — don't batch multiple sections into one commit, and don't commit mid-section.
- Only pass `discard_changes: true` after step 9's ancestor check passes.
