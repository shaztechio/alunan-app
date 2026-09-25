# Shared data contracts

Status: proposed version 1; no serializer or runtime has been implemented.
Behavior is defined by [FEATURES.md](FEATURES.md). These contracts describe data
meaning shared by all three apps, regardless of implementation language.

## General rules

- Text is UTF-8; JSON field names use camelCase; timestamps are UTC ISO 8601.
- Byte counts and file lengths are nonnegative integers; unknown values are null,
  not zero. Digests are lowercase SHA-256 hex strings.
- Every persisted record carries `schemaVersion`. An unsupported version must
  produce a useful compatibility error without modifying the original.
- Save records atomically. Ignore unknown optional fields when reading and retain
  them when rewriting a compatible project. Required incompatible semantics need
  a new schema version.
- File paths in portable records are relative, use `/`, and must resolve within
  their container. Reject absolute paths, traversal, alternate streams, reserved
  aliases, case-insensitive collisions, and symlink escapes on every platform.

## Model catalog and manifests

The app ships immutable catalog data with its engine/runtime. There are no real
Lagu model URLs, digests, or size promises in this initial spec; release artifacts
must contain verified values before a model can be offered.

| Record | Required meaning |
| --- | --- |
| Catalog | `schemaVersion`, `catalogVersion`, and supported `profiles`. |
| Profile | Stable `profileId`, user-facing name, model family, runtime format, quantization, supported capabilities, compatible engine versions, generator/decoder revisions, supported platform/backend combinations, and required asset references. |
| Asset | Stable `assetId`, immutable `revision`, `relativePath`, `sizeBytes`, `sha256`, role, and curated source identity/locator. All assets in a selected profile are required; optional capabilities use their own asset sets. |
| Source | Stable `sourceId`, canonical HTTPS locator at an immutable revision, and source attribution. Temporary redirect URLs are transport data only. |
| License | Model/component name, license identifier or title, bundled notice path, source URL, and applicable additional terms. |

An asset list can be embedded or supplied by an external manifest whose SHA-256
is embedded in the catalog. A remote file and a digest from the same unpinned
endpoint alone do not establish the catalog's expected artifact identity.

Cache identity comprises source ID, runtime format, profile/artifact revision,
and expected digest. GGUF, MLX, and original PyTorch weights are distinct assets.
Files can be reused between compatible profiles only when their exact identity
matches; a model name alone is insufficient.

## Cache records and completion

Use an OS-appropriate application-data root. A conceptual layout is:

```text
models/
  <source-id>/<runtime-format>/<profile-id>/<revision-id>/
    manifest.json
    files/<relative-asset-path>
    files/<relative-asset-path>.incomplete
    transfer.json
    ready.json
```

Catalog IDs must be safe opaque path components, not raw URLs. If identifiers
require mapping, use a stable collision-resistant encoding consistently across
implementations. Locks and temporary records are implementation details.

- `transfer.json`: artifact/source identity, expected digest/size, partial path,
  and response validators when available. The actual partial file length is the
  resume offset; a stale saved counter never authorizes appending past its end.
- `ready.json`: schema/profile/revision/runtime/manifest identity, required asset
  identities, actual verified digests, lengths, verification times, and local
  file metadata used for later change detection. No credentials or signed URLs.
- Write `ready.json` only after every required file has been verified and promoted.
  A matching receipt plus existing unchanged files permits offline reuse.
- Missing/changed files, incompatible identities, or active incomplete markers
  for required assets invalidate readiness. Staging a different revision must
  not invalidate a complete older revision.
- Verification uses the full file, including any resumed prefix. A bad partial
  cannot be relabeled as complete. A known-good older revision remains intact
  while a new revision is prepared.

## Portable projects

A project is a folder with `project.json`, a saved draft, and uniquely identified
takes. Each take contains its audio and any generated score. A portable project
does not include model weights or depend on an absolute cache path.

| Project data | Required meaning |
| --- | --- |
| Identity | `schemaVersion`, `projectId`, title, creation/update timestamps. |
| Draft | Lyrics, style, requested profile, seed choice, supported user settings. |
| Take | `takeId`, request snapshot, effective seed/settings, model and decoder revisions/digests, quantization, runtime/engine version, timestamps, status, warnings, and relative audio/score paths. |
| Audio | Actual sample rate, channel count, frame count/duration, and format. MVP export is WAV. |
| Status | Completed, completed with truncation warning, cancelled, failed, or interrupted. Only takes with a finalized playable file appear as playable results. |

Only finalized takes are added to the successful results index. Interrupted
write files are distinguished from completed audio. The app must preserve the
recorded request even if a compatible alternate backend is selected for a later
take. A seed records an input; it does not guarantee identical results across
engines, quantizations, hardware, or runtime versions.

## Download observations

Implementations share these semantics, whether progress comes from C# or Swift:

`jobId`, `phase`, `profileId`, `assetId`, current filename, retained unique bytes,
total bytes or null, current-file retained bytes/total, actual network bytes
received, last-receipt time, attempt elapsed time, and optional retry deadline.

Completion and network traffic are separate counters. Each reconnect may receive
bytes again; those bytes affect speed but must not double-count completion.
Rejected/discarded bytes leave completion. Stale job IDs must not update an active
job or turn a cancelled job into a successful one.
