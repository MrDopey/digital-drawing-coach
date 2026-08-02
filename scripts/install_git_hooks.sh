#!/usr/bin/env bash
# One-time per-clone setup: point git at the repo's tracked hooks/ directory
# (`.git/hooks/` isn't version-controlled, so this can't be automatic).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

chmod +x "$repo_root/hooks/pre-commit"
git -C "$repo_root" config core.hooksPath hooks

echo "Git hooks installed (core.hooksPath -> hooks/)."
echo "The pre-commit hook runs the design-system compliance check locally."
echo "Bypass with 'git commit --no-verify' if truly necessary — CI still enforces it."
