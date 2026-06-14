---
name: dc-ship
description: Implement, archive, and merge a Drawing Coach change. Wraps opsx:apply + opsx:archive (with spec sync) + worktree merge into main. Use after /dc-propose when ready to ship.
license: MIT
compatibility: Requires openspec CLI, git, and an active worktree session.
---

Implement, archive, and merge a Drawing Coach change end-to-end.

This is the project-specific wrapper that runs the full ship sequence:
**apply → archive (with spec sync) → commit → merge worktree → cleanup**.

---

**Steps**

1. **Apply: implement all tasks**

   Use the **Skill tool** to invoke `opsx:apply` with the change name as args.
   Work through all pending tasks. Do not proceed to archive until all tasks
   are marked complete (`- [x]`).

2. **Archive: sync specs and archive the change**

   Use the **Skill tool** to invoke `opsx:archive` with the change name as args.
   This handles:
   - Delta spec sync to `openspec/specs/<capability>/spec.md`
   - Moving the change directory to `openspec/changes/archive/YYYY-MM-DD-<name>/`

3. **Commit all changes in the worktree**

   Stage and commit everything in the current worktree branch:
   ```bash
   git add -A
   git commit -m "feat: <change-name> — <one-line summary>

   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
   ```

4. **Merge the worktree branch into main**

   From the main repo (not the worktree):
   ```bash
   git -C <repo-root> merge <worktree-branch> --no-ff -m "Merge <worktree-branch>: <change-name>

   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
   ```

   The repo root is the parent of `.claude/worktrees/` — derive it from the
   worktree path (e.g. `/workspaces/digital-drawing-coach/.claude/worktrees/add-user-auth`
   → repo root is `/workspaces/digital-drawing-coach`).

   The worktree branch name follows the pattern `worktree-<directory-name>` and can
   be confirmed with `git branch --show-current` run inside the worktree.

5. **Verify and report**

   After merging, confirm:
   - The merge commit appears on main (`git -C <repo-root> log --oneline -3`)
   - No stray untracked files remain in `openspec/changes/<name>/` on the shared checkout
     (the orphan-prevention guardrail from `/dc-propose` should have eliminated this,
     but check anyway)

   If an orphaned `openspec/changes/<name>/.openspec.yaml` is found on the shared
   checkout after merging, move it to the archive directory and commit the fix:
   ```bash
   mv openspec/changes/<name>/.openspec.yaml \
      openspec/changes/archive/YYYY-MM-DD-<name>/.openspec.yaml
   rm -rf openspec/changes/<name>
   git add -A && git commit -m "fix: move orphaned .openspec.yaml to archive for <name>"
   ```

**Output On Success**

```
## Shipped: <change-name>

✓ Tasks implemented (N/N complete)
✓ Specs synced to openspec/specs/
✓ Archived to openspec/changes/archive/YYYY-MM-DD-<name>/
✓ Merged into main (<short-sha>)
```

**Guardrails**
- Do not merge until all tasks are complete and the archive step has succeeded
- Always use `--no-ff` on the merge to preserve the branch history
- Check for orphaned `.openspec.yaml` files after every merge and fix them immediately
- If the merge has conflicts, resolve them before reporting success
