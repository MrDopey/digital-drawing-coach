---
name: dc-propose
description: Propose a new Drawing Coach change — worktree-aware wrapper around opsx:propose. Handles worktree naming, prevents orphaned .openspec.yaml files, and generates all artifacts in one step. Use instead of /opsx:propose for this repo.
license: MIT
compatibility: Requires openspec CLI and EnterWorktree tool.
---

Propose a new Drawing Coach change with full worktree isolation.

This is the project-specific wrapper around `opsx:propose`. It adds two
guardrails critical to this repo's workflow:

1. **Worktree naming** — the worktree is named after the change, not a random slug.
2. **Orphan prevention** — the worktree is entered BEFORE `openspec new change` runs,
   so `.openspec.yaml` is created inside the isolated copy, not the shared checkout.

---

**Steps**

1. **Determine the change name**

   If the user described what they want to build, derive a kebab-case name
   (e.g., "add user authentication" → `add-user-auth`).

   If no clear input, use **AskUserQuestion** to ask:
   > "What change do you want to work on? Describe what you want to build or fix."

   Do NOT proceed without a change name.

2. **Enter a named worktree BEFORE creating the change**

   Call `EnterWorktree` with `name: "<change-name>"` — the exact kebab-case name
   derived in step 1.

   **Why this order matters:** `openspec new change` creates the change directory and
   `.openspec.yaml` wherever the current working directory points. If `EnterWorktree`
   is called *after* `openspec new change`, the `.openspec.yaml` lands in the shared
   checkout and becomes an orphaned file that must be manually cleaned up after merging.
   Entering the worktree first ensures the entire change lives in the isolated copy.

   **Naming convention:** Passing the change name as `name` makes the worktree branch
   and directory reflect the change (e.g., `worktree-add-user-auth`), keeping the
   agent view readable instead of showing a random slug.

3. **Create the change** (now inside the worktree)

   ```bash
   openspec new change "<name>"
   ```

4. **Invoke opsx:propose for artifact generation**

   Use the **Skill tool** to invoke `opsx:propose` with the change name as args.
   This generates proposal.md, design.md, specs/, and tasks.md following the
   standard spec-driven workflow.

5. **Confirm worktree and change are aligned**

   After artifacts are created, remind the user:
   - Worktree: `<worktree-path>`
   - Change: `<name>`
   - Next step: `/dc-ship` to implement, archive, and merge

**Output**

```
## Proposed: <change-name>

Worktree: .claude/worktrees/<change-name>/
Change: openspec/changes/<change-name>/

[artifact summary from opsx:propose]

Ready to implement. Run `/dc-ship` to work through tasks, archive, and merge.
```

**Guardrails**
- ALWAYS enter the worktree before running `openspec new change` — never after
- ALWAYS pass the change name as `name` to `EnterWorktree`, never leave it blank
- If the worktree already exists (e.g. resuming), enter it with `path` instead of `name`
- If a change with the same name already exists in the worktree, ask the user whether to continue it or pick a new name
