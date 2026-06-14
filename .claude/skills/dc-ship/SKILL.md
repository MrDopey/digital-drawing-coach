---
name: dc-ship
description: Implement, archive, and merge a Drawing Coach change into main. Use after /dc-propose when ready to ship.
license: MIT
---

1. Invoke `opsx:apply` with the change name — work through all tasks until complete.
2. Invoke `opsx:archive` with the change name — sync delta specs and archive.
3. Commit everything in the worktree:
   ```
   git add -A && git commit -m "feat: <change-name> — <summary>\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
   ```
4. Merge into main (repo root is two levels above `.claude/worktrees/<name>`):
   ```
   git -C <repo-root> merge <worktree-branch> --no-ff -m "Merge <branch>: <change-name>\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
   ```
   Branch name: `git branch --show-current` inside the worktree.
5. Check for orphaned `.openspec.yaml` on the shared checkout. If found, move it to the archive dir and commit the fix immediately.

**Guardrails:** Always use `--no-ff`. Do not merge before all tasks are complete and archive succeeds.
