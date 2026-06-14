---
name: op-custom-propose
description: Propose a new Drawing Coach change with worktree isolation. Use instead of /opsx:propose for this repo.
license: MIT
---

1. Derive a kebab-case change name from the user's description. Ask if unclear.
2. `EnterWorktree` with `name: "<change-name>"` — **before** anything else.
   This prevents an orphaned `.openspec.yaml` on the shared checkout and names
   the worktree branch after the change instead of a random slug.
3. `openspec new change "<name>"` (now inside the worktree).
4. Invoke `opsx:propose` with the change name to generate all artifacts.
5. Tell the user: worktree path, change name, and to run `/op-custom-ship` when ready.
