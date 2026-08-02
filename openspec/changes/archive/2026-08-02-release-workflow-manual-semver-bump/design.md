## Context

`release.yml` currently has three jobs: `build-binaries` (matrix over ubuntu/windows/macos, triggered by a `v*` tag push), `create-release` (attaches the zips to a GitHub Release via `softprops/action-gh-release`), and `publish-packages` (pushes the same zips to GHCR as OCI artifacts via `oras`). Version is derived at build time from `GITHUB_REF_NAME` — `scripts/build_version.py` writes it into `src/drawing_coach/_version.py`, which the app displays in its About dialog and logs on startup. `pyproject.toml`'s `version` field (`0.1.0`) is currently unused at runtime; it's inert metadata.

We're moving to a maintainer-driven, tagless-trigger model: someone runs the workflow from the Actions tab (or `gh workflow run`), picks a bump size, and the workflow does the rest — build, release, then bump-and-commit. This removes the "someone has to git-tag the right commit with the right version string" step entirely, and removes the OCI publishing job, which nothing in this repo consumes.

Note: the `docker-distribution` spec still describes a `build-docker` job keyed off `v*` tag pushes, but that job was already removed from `release.yml` in a prior commit (`e229bc7`, "chore: github removed docker component") without the spec being updated. That drift predates this change and this change doesn't touch Docker; it's called out here so it isn't mistaken for something this design introduces or fixes.

## Goals / Non-Goals

**Goals:**
- Trigger releases only via `workflow_dispatch`, with a required `bump` choice input (`patch` | `minor` | `major`).
- Make `pyproject.toml`'s `version` field the single authoritative version source, always a valid semver string.
- Build binaries using the version that's currently committed (the version being released), not one derived from a tag.
- After a successful release, bump the version per the chosen input and commit it back to `main`, so `main` always shows a semver value that previews the next release.
- Remove OCI/`oras` publishing and its dependency entirely.
- Use no third-party GitHub Actions at all in this workflow — only actions published and maintained by GitHub itself (`actions/*`), plus the official `gh` CLI (preinstalled on GitHub-hosted runners) and plain `git`/Python, for every step including creating the release and committing the version bump.
- Make the "`main` previews the next release" fact visible inside the app itself: the tray menu's "About" entry and About dialog show `<pyproject-version>-prerelease` (e.g. `0.2.0-prerelease`) rather than a bare `dev` label when running an unbuilt copy from source.

**Non-Goals:**
- Storing a suffixed value in `pyproject.toml` itself — the committed `[project].version` field stays a plain semver string (e.g. `0.2.0`), bumped as-is by `bump_version.py`. The `-prerelease` suffix is purely a runtime display computed by the app when it detects it's running an unbuilt/from-source copy; it is never written to any file. Callers who want to distinguish "released" from "previewed" programmatically do so by checking whether a matching `v<version>` tag/release exists, not by parsing the suffix.
- Reworking `docker-distribution` or reinstating its build job — out of scope; flagged as a pre-existing spec/reality drift for separate cleanup.
- Rich changelog categorization (by commit type, conventional-commit parsing, etc.) beyond a flat bullet list of commit subjects — the commit-log fallback (see Decisions) is intentionally simple, not a changelog-generation tool.
- Enforcing semver on arbitrary manual edits to `pyproject.toml` outside the release workflow (e.g. a pre-commit hook) — the workflow is the sanctioned path; out of scope here.

## Decisions

**Version source: `pyproject.toml` `[project].version`, read via `tomllib`.**
This is already a real, present field (`0.1.0`) that PyPI/hatchling-style tooling expects to be the source of truth, and it's plain data a workflow step can read and rewrite with a small regex/`tomllib` script — no new file or format needed. Alternative considered: keep a separate `VERSION` text file. Rejected — it'd duplicate the version identity `pyproject.toml` already carries and give two things to keep in sync.

**Bump implemented as a small first-party script, not a third-party bump action.**
`scripts/bump_version.py <patch|minor|major>` parses the current `X.Y.Z`, increments the right component (resetting lower components to `0`), and rewrites `pyproject.toml` in place. Considered `callowayproject/bump-my-version` and similar actions — they're reasonable, but for three fixed, simple bump rules a ~15-line script is easier to audit than trusting another action's release process, and it keeps the "no third-party actions" goal literal: the fewer external actions in the trust chain, the better.

**Release creation via the official `gh` CLI, not `softprops/action-gh-release`.**
The release-creation step runs `gh release create "v<version>" artifacts/*.zip ...` (authenticated via `GITHUB_TOKEN`), instead of the third-party `softprops/action-gh-release`. `gh` is GitHub's own CLI, preinstalled on every GitHub-hosted runner, and covers exactly what was needed — creating a tagged release and uploading multiple assets — without adding an external action to the trust chain at all. This was the last third-party action in the workflow; removing it means every remaining step is either a first-party `actions/*` action, the official `gh` CLI, or plain `git`/Python.

**Release notes: `--generate-notes` when PRs exist in range, a `git log` commit-list fallback otherwise.**
This repo doesn't use a PR-based workflow — commits land on `main` directly. GitHub's `--generate-notes` groups its output by merged PRs; with none in range, the body degrades to little more than a `Full Changelog: vX...vY` compare link. So the `create-release` step first checks whether any PRs were merged since the previous release (`gh pr list --state merged --search "merged:>=<prev-release-date>" --json number --jq 'length'`, using the previous release's tag date as the cutoff — or the repo's creation date if there is no previous release), and:
- if that count is `> 0`, runs `gh release create ... --generate-notes` as normal (some PRs may exist even in a mostly-direct-commit history — no reason to discard the richer output when they do);
- otherwise, builds notes from `git log <prev-tag>..HEAD --pretty=format:"- %s (%h)"` (or the full history if there's no previous tag) written to a temp file, passed via `gh release create ... --notes-file`.

This stays entirely within `git`/`gh` — no new dependency — and produces a real bullet list of what changed on the common path (direct commits) instead of the empty PR-based body `--generate-notes` alone would otherwise silently produce. Considered always using the commit-log fallback (simpler, one code path) — rejected, because it would throw away the richer PR-grouped output on the (less common but possible) release that did go through a PR.

**Commit-back done with plain `git`, not a third-party "auto-commit" action.**
The job already has `permissions: contents: write` for the `gh release create` step; the same `GITHUB_TOKEN` can push a commit directly (`git -c user.name=... -c user.email=... commit` + `git push`) after `actions/checkout` (which wires up the token-authenticated remote automatically). Considered `stefanzweifel/git-auto-commit-action` — popular and reputable, but genuinely unnecessary here: it exists to make committing arbitrary working-tree diffs convenient, and we have exactly one deterministic file edit to commit, so plain `git` is simpler to reason about and keeps this third-party-action-free.

**Ordering: build → release (tag = current version) → bump → commit.**
The binaries built and released must embed the version that's *currently* committed — that's the version being shipped. Bumping first would release binaries labeled with a version nothing has shipped yet. So the job graph is: `build-binaries` (matrix, reads current `pyproject.toml` version, unchanged per-runner) → `create-release` (needs `build-binaries`; runs `gh release create "v<current-version>" ...`, which creates that tag against the commit the job runs on) → `bump-version` (needs `create-release`; re-reads current version, applies the chosen bump, commits, pushes to `main`). Each job re-derives the current version from a fresh checkout rather than passing it through job outputs, since every job runs against the same pre-bump commit until the last job's own commit — simpler than threading an output through three jobs for a value every job can cheaply recompute itself.

**`build_version.py` now reads `pyproject.toml` instead of `GITHUB_REF_NAME`.**
`GITHUB_REF_NAME` on a `workflow_dispatch` run is just the branch name (`main`), not a version — so the tag-derived version logic no longer means anything and is replaced with a `tomllib` read of `pyproject.toml`. A real release build still overwrites `src/drawing_coach/_version.py` with the concrete released version string in the CI build's ephemeral working copy, never committing that overwrite back — a built binary's version is unaffected by the change below.

**Unbuilt/from-source display becomes `<pyproject-version>-prerelease`, computed at import time, not a second committed literal.**
`src/drawing_coach/_version.py` changes from a static `__version__ = "dev"` constant to a small module that reads the current version straight out of `pyproject.toml` (walking up from `_version.py`'s own path to the repo root, the same relative layout `build_version.py` already assumes) and sets `__version__ = f"{version}-prerelease"`; if `pyproject.toml` can't be found (e.g. a non-editable installed wheel with no source tree alongside it), it falls back to the literal `"dev"` rather than raising. This keeps a single read path for "what version is `main` currently on" — the same value `bump_version.py` writes and `build_version.py` embeds — rather than introducing a second, independently-committed placeholder string that could drift out of sync with `pyproject.toml`. Considered leaving `_version.py` as a static `"dev"` string and only reformatting it for display at the two `main_window.py` call sites — rejected, because `__main__.py`'s startup log line also reads `__version__` directly, and duplicating the "is this dev-or-suffix" logic at each call site (rather than once in `_version.py`) is exactly the kind of decision that should live in one place.

**Concurrency guard on the workflow.**
Add a `concurrency: group: release, cancel-in-progress: false` (queue, don't cancel) so two manual dispatches can't race on reading/bumping/committing the version and corrupt `main`'s history with two conflicting bump commits.

## Risks / Trade-offs

- **[Risk]** The bump-and-commit push to `main` could be rejected if `main` is branch-protected against direct pushes (e.g. requiring PRs). → Mitigation: this is a repo-setting question outside this change's control; tasks.md includes a check/adjustment of branch protection (allow the `GITHUB_TOKEN`'s actor, or a required status-checks exemption for this workflow) as an implementation task, not assumed away.
- **[Risk]** If the bump-and-commit step fails after the release is already published, the release ships successfully but `main` is left un-bumped (still showing the just-released version, not a preview of the next one) until someone re-runs or manually fixes it. → Mitigation: the bump step is a small, low-failure-surface operation (file rewrite + git push); acceptable residual risk given the alternative (a single all-or-nothing transaction across a GitHub Release and a git push) isn't achievable with GitHub Actions primitives.
- **[Risk]** A maintainer picks the wrong bump size (e.g. `patch` when the changes were breaking) — this is a manual, judgment-dependent step now with no tag to double-check against beforehand. → Mitigation: the workflow's confirmation step (dispatch UI) should surface the resulting version number before the irreversible commit/release happens; covered as a task, not a spec requirement change.
- **[Trade-off]** Dropping OCI/GHCR publishing removes a distribution channel. → Accepted: nothing in this repo or its docs currently references pulling binaries via `oras`/GHCR; the GitHub Release remains the sole and already-primary download path per the original design doc.
- **[Risk]** Reading `pyproject.toml` at import time for the `-prerelease` display adds a filesystem lookup (and a path-resolution assumption — repo root is a fixed number of parents above `_version.py`) to a module imported on every app startup. → Mitigation: the lookup is a single small local file read with a `try`/`except` fallback to `"dev"`; a built binary never hits this path at all since `build_version.py` overwrites the file with a plain literal before packaging.

## Migration Plan

1. Land `scripts/bump_version.py`, update `scripts/build_version.py` to read `pyproject.toml`, and update `src/drawing_coach/_version.py` to compute the `-prerelease` fallback.
2. Update `.github/workflows/release.yml`: swap the trigger, drop `publish-packages`, add the `bump-version` job, add the concurrency group.
3. Verify branch protection on `main` permits the workflow's push (adjust if needed).
4. First manual dispatch after merge should be treated as a dry run on a fork or a low-stakes `patch` bump to confirm the tag/release/bump-commit sequence behaves as designed before relying on it for a real release.
5. No rollback of already-published releases is needed if something goes wrong — worst case is a missing or incorrect bump commit on `main`, which is a one-line manual fix.

## Open Questions

- Should the workflow refuse to run (or warn) if `main`'s current version doesn't parse as valid semver, rather than silently failing the bump? Leaning yes; left as a task-level detail rather than a design decision since it's a straightforward validate-and-fail-fast step.
- Does `main` currently have branch protection rules that would block this workflow's direct push? Needs to be checked against the actual repo settings, not something this document can determine.
