---
name: op-custom-propose
description: Propose a new Drawing Coach change with worktree isolation. Use instead of /opsx:propose for this repo.
license: MIT
---

1. Derive a kebab-case change name from the user's description. Ask if unclear.
2. `EnterWorktree` with `name: "<change-name>"` — **before** anything else.
   This names the worktree branch after the change and ensures all openspec commands
   run inside the worktree, preventing a stray `.openspec.yaml` on the shared checkout.
3. Invoke `openspec-propose` with the change name — it runs inline in the current session
   and inherits the worktree CWD, so `openspec new change` and all artifact generation
   happen inside the worktree, not on the shared checkout.
4. Tell the user: worktree path, change name, and to run `/op-custom-ship` when ready.
