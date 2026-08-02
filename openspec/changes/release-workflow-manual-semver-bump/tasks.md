## 1. Version source & bump tooling

- [x] 1.1 Update `scripts/build_version.py` to read the version from `pyproject.toml`'s `[project].version` (via `tomllib`) instead of the `GITHUB_REF_NAME` env var, and write it to `src/drawing_coach/_version.py` as before.
- [x] 1.2 Add `scripts/bump_version.py <patch|minor|major>`: parses the current `MAJOR.MINOR.PATCH` from `pyproject.toml`, applies the bump (resetting lower components to `0`), rewrites `pyproject.toml` in place, and prints the new version. Fail fast with a clear error if the current version isn't valid semver.
- [x] 1.3 Remove the `GITHUB_REF_NAME`-based version derivation from `scripts/package.sh` and `scripts/package.ps1` now that `build_version.py` is the single place version is resolved; have them just invoke `build_version.py` and read its output (or re-read `pyproject.toml`) for the zip filename.
- [x] 1.4 Add/update a unit test covering `bump_version.py`'s patch/minor/major arithmetic (including the reset-lower-components behavior) and its failure on non-semver input.
- [x] 1.5 Change `src/drawing_coach/_version.py` from a static `__version__ = "dev"` constant to logic that reads the current version out of `pyproject.toml` (resolved relative to `_version.py`'s own path) and sets `__version__` to `f"{version}-prerelease"`, falling back to the literal `"dev"` if `pyproject.toml` can't be found.
- [x] 1.6 Add/update a unit test covering `_version.py`'s new behavior: reads `pyproject.toml` and appends `-prerelease` when present; falls back to `"dev"` when it isn't.

## 2. Release workflow

- [x] 2.1 Change `.github/workflows/release.yml`'s trigger from `push: tags: ["v*"]` to `workflow_dispatch` with a required `bump` input (`type: choice`, options `patch`/`minor`/`major`).
- [x] 2.2 Add `concurrency: group: release, cancel-in-progress: false` at the workflow level so concurrent dispatches queue instead of racing on the version bump/commit.
- [x] 2.3 Update the `build-binaries` matrix job so each platform build reads the current `pyproject.toml` version (via task 1.1's updated `build_version.py`) rather than relying on a tag.
- [x] 2.4 Update `create-release` to compute `v<current-version>` from `pyproject.toml` and determine the previous release's tag/date (if any) via `gh release view --json tagName,createdAt` (or equivalent).
- [x] 2.5 Before creating the release, check for merged PRs since the previous release (`gh pr list --state merged --search "merged:>=<prev-release-date>" --json number --jq 'length'`, or since repo creation if there's no previous release). If the count is `> 0`, run `gh release create "v<current-version>" artifacts/*.zip --generate-notes`. Otherwise, build a notes file from `git log <prev-tag>..HEAD --pretty=format:"- %s (%h)"` (full history if no previous tag) and run `gh release create "v<current-version>" artifacts/*.zip --notes-file <file>`. Both paths authenticate via `env: GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}` and replace the `softprops/action-gh-release` step — no third-party action for this step.
- [x] 2.6 Remove the `publish-packages` job entirely, including the `oras-project/setup-oras` step and the GHCR login/push steps.
- [x] 2.7 Add a `bump-version` job (`needs: create-release`) that checks out `main`, runs `scripts/bump_version.py ${{ inputs.bump }}`, and commits + pushes the resulting `pyproject.toml` change directly to `main` using the workflow's own `GITHUB_TOKEN` (no third-party commit action).
- [ ] 2.8 Confirm `main`'s branch protection (if any) permits this direct push from the workflow's token; adjust the ruleset or use an appropriate bypass/exception if it currently blocks direct pushes.
- [x] 2.9 Have the `bump-version` job validate the current version is valid semver before bumping, failing the job with a clear message if not (rather than silently producing a malformed version).

## 3. Verification

- [ ] 3.1 Dry-run the updated workflow (e.g. on a fork, or as a real `patch` release if appropriate) to confirm the build → release → bump-and-commit sequence behaves as designed and `main` ends up with the previewed next version.
- [x] 3.2 Confirm the About dialog and startup log show the correct embedded version for a binary built via the updated `build_version.py`, and separately confirm an unbuilt run from source shows `<pyproject-version>-prerelease` in the tray menu's About entry and About dialog.
- [ ] 3.3 Confirm the release-notes branching: a dry run with no merged PRs in range produces a commit-log bullet list body; if feasible, also confirm a release with at least one merged PR in range produces the normal `--generate-notes` PR-grouped body.

## 4. Documentation

- [ ] 4.1 Update README.md's release/versioning-relevant sections from a developer's perspective: how to cut a release now (dispatch the workflow with a bump choice) instead of pushing a tag, and that OCI/GHCR binary publishing no longer exists.
- [ ] 4.2 Update `.claude/CLAUDE.md`'s Tech Stack / Build row (and anywhere else it describes the release process) to reflect the `workflow_dispatch` trigger, semver-in-`pyproject.toml` as the version source, and the removal of OCI/GHCR binary publishing.
- [ ] 4.3 Review `openspec/config.yaml`'s `rules.tasks`/`rules.proposal` for a clear, recurring gap this change reveals (e.g. a rule about CI/workflow changes needing a branch-protection check called out) — propose an addition only if there's a genuine recurring pattern, not just to document this one change.

## 5. Final Verification

- [ ] 5.1 Run `uv run pytest` and confirm all tests pass.
