---
name: op-custom-ready
description: Enter the worktree for an existing Drawing Coach change and load its context. Use when a change has already been proposed and you need to resume work on it (e.g. before running /op-custom-ship).
license: MIT
disable-model-invocation: true
---

1. Take the change name from the user's input. If unclear, run `openspec list` and ask the user to select.
2. `EnterWorktree` with `name: "<change-name>"`.
3. Run `openspec instructions apply --change "<name>" --json` and read the context files it returns so the session has full knowledge of the proposal, design, specs, and task state.
4. Tell the user: worktree path, current task progress, and that they can run `/op-custom-ship` to implement and merge.
