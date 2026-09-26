# Lagu repository guidance

Phase 0 feasibility work is authorized and in progress. The repository contains
specifications and developer research tools; native application implementation
has not started. Keep Phase 0 experiments separate from production app code.

- Read `spec/FEATURES.md` before changing observable behavior. It is the shared
  source of truth for Windows, Linux, and macOS.
- Update the specification first when changing a feature. Keep requirement IDs
  stable and update the corresponding acceptance scenarios.
- `spec/DATA-FORMATS.md` defines shared persisted contracts;
  `spec/IMPLEMENTATION-PLAN.md` records engineering decisions and open questions.
  Neither should introduce product behavior that conflicts with the feature spec.
- Record platform differences explicitly in the shared specification. A feature
  implemented on one platform is not complete across platforms until the other
  implementations pass its acceptance scenarios or have a documented exception.
- Treat bunyi-app as a read-only reference unless separately authorized to edit it.
- Preserve the requested UI stack: Windows WinForms, Linux GTK 4/Gir.Core, macOS
  Swift with native Apple UI frameworks.
- Bundle runtime dependencies, except vendor GPU runtime packs, which the app
  downloads on demand under `spec/FEATURES.md` MOD-015. Models are downloaded on
  demand by the app; users must not manage terminals, dependency installers, or
  inference servers.
- Keep research weights, environments, source checkouts, and generated audio in
  ignored `.phase0/`. Track compact measurements, source/model pins, and findings
  under `docs/validation/phase0/`; never count missing hardware as passing.

## How changes land: pull requests only

Every change reaches `main` through a pull request: code, spec, docs, website,
workflows, and one-line fixes, by people and agents alike. The only exception is
the automated version-bump commit a release workflow pushes (see Releases).

1. Branch off `main`, commit there, push, and open a PR. Do not push commits
   straight onto `main` to save a step.
2. Title the PR as a Conventional Commit: `<type>[(scope)][!]: <summary>`, for
   example `feat(windows): add a stop button to the composer`. Types: `feat`,
   `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`;
   `!` marks a breaking change. Lowercase after the colon, imperative mood, no
   trailing full stop. Scopes name the area: `windows`, `linux`, `macos`,
   `dotnet` (shared Windows/Linux code), `spec`, `site`, `engine`, `phase0`.
   Squash-merged titles become release-note lines, so a non-conventional title
   ends up under "Other changes".
3. CI must pass on the PR before merging.
4. Stacked PRs merge bottom-up: merge the PR based on `main` first, retarget the
   next one to `main`, then merge it. Merging out of order strands the upper work.

## Feature changes and platform parity

Whenever a feature is added, removed, or changes observable behavior:

1. Update `spec/FEATURES.md` first, in the same PR as the implementation (or in a
   spec-only PR that lands before it). Add or amend requirement IDs, acceptance
   scenarios, and the platform parity table; update `spec/DATA-FORMATS.md` if a
   persisted contract changes. Removing a feature removes or marks its
   requirements in the spec; it is not silently dropped from one app.
2. Check every other platform (Windows, Linux, macOS) against the changed
   requirements. Say in the PR description, per platform, whether the change is
   implemented, not applicable (with the spec's documented exception), or
   missing.
3. For each platform where it is missing, file a GitHub issue in
   `shaztechio/alunan-app` before merging. Title it with the platform and the
   change, name the requirement and acceptance-scenario IDs, and link the PR.
   Reference the issue in the PR description and in any parity note in the spec.
   A change that lands on one platform with no spec update and no tracking issue
   is incomplete.
4. Update the website copy (`docs/index.html`) in the same PR when the change
   alters anything the site describes; see `docs/README.md`.

## Releases

Alunan has no release workflow or published release yet; Phase 7 builds them.
Implement and operate them on the model proven in bunyi-app:

- **Separate release families per codebase.** The .NET app (Windows and Linux)
  and the Swift app (macOS) release independently, with their own tag namespace
  (`dotnet-v<x.y.z>` and `macos-v<x.y.z>`) and their own release workflow. One
  family's tag must never start the other's release.
- **Starting a release.** Run the family's release workflow from GitHub Actions
  with a bump of `patch`, `minor`, or `major` (or an exact version). The
  workflow edits the single version source for that app, commits, tags, pushes,
  builds, and publishes. A `none` bump builds everything and publishes nothing.
  A run started by a pushed tag must refuse to build when the tag disagrees with
  the version in source.
- **What a release publishes.** A GitHub Release per tag with every installer
  or package for that family and a `.sha256` beside each file. Standard
  packages carry no model weights or vendor GPU runtime packs (APP-006,
  MOD-015). Installation checks gate publication; a partially uploaded asset
  set is not advertised.
- **Release notes.** Write `release-notes/<tag>.md` in a PR before running the
  release when the changes need prose; the workflow uses it verbatim. Otherwise
  the workflow generates notes from the Conventional Commit subjects since the
  previous tag of the same family, limited to that app's paths so one family's
  notes never list the other's work. Links in release notes point at the tag,
  not `main`. Do not claim code signing, hardware support, or features the
  release does not have.
- **Website refresh on every release.** After a successful stable release, the
  release workflow dispatches the website workflow on `main`
  (`gh workflow run pages.yml --ref main`), and a manually published stable
  release does the same. The site build reads published releases, picks the
  highest complete stable version per family (ignoring drafts, prereleases,
  and incomplete asset sets), and renders download links and version badges
  from it, so no manual edit updates a version number. Feature and spec changes
  reach the site through the PRs that made them (see Feature changes); before
  a release, check that `docs/index.html` matches the released `spec/FEATURES.md`
  and update it in a PR if not. Until the first release, the site has no
  download links and must not imply downloads exist.

## Active workspace

The repository moved to `C:\Users\shazron\Documents\git\github.com\shaztechio\alunan-app`.
Use that explicit working directory if this chat still starts in `lagu-app`.
See `docs/workspace-relocation.md`. The research venv was recreated from the hash
lock on 2026-09-26; keep historical evidence intact.
