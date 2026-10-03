# Alunan shared feature specification

Status: Phase 0 research baseline; native application features are unimplemented.
Last updated: 2026-09-26.

This is the **source of truth for observable features and behavior** on Windows,
Linux, and macOS. MUST requirements are acceptance conditions. Implementation
choices and research findings belong in [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md)
and [REFERENCES.md](REFERENCES.md). Persisted contracts belong in
[DATA-FORMATS.md](DATA-FORMATS.md).

Requirement IDs remain stable when text changes. Change this document before
implementing a feature change, then update every platform and its acceptance
evidence. A native layout may differ; behavior, data meaning, and recovery must
agree. No platform implementation silently overrides the spec. Open engineering
questions are not claims of implemented support.

## 1. Product and scope

Alunan lets a non-technical user install an application, enter lyrics and a musical
style, generate music locally, listen, and save the result.

| ID | Requirement |
| --- | --- |
| APP-001 | Windows MUST use WinForms; Linux MUST use GTK 4 through Gir.Core; macOS MUST use Swift with native Apple UI frameworks. |
| APP-002 | A supported machine MUST need only the Alunan application installation. The package MUST include the required application runtimes, engine, and redistributable libraries, except vendor GPU runtime packs that the app itself prepares under MOD-015. No terminal, Python/pip, Homebrew, .NET, GTK, or CUDA toolkit setup may be delegated to the user. |
| APP-003 | The app MUST start, supervise, stop, and clean up its generation helper automatically. No separately launched server, console window, port entry, service configuration, or login is required. |
| APP-004 | Music generation, playback, projects, and installed-model checks MUST run locally. Lyrics, scores, reference media, and generated audio MUST NOT be uploaded for inference. No telemetry is included in the MVP. |
| APP-005 | The app MUST download model data, and any GPU runtime pack the selected profile requires (MOD-015), only when needed for a user-requested operation, or when the user explicitly selects Download in model settings. Launching the app alone MUST NOT download models or runtime packs. |
| APP-006 | Standard application installers MUST contain runtime dependencies and MUST NOT bundle model weights or vendor GPU runtime packs. Internet is needed to acquire missing models and runtime packs; a complete installed model and its runtime pack MUST work offline. Separate model packs support offline import. This supersedes the earlier plan to bundle a default model in every installer; excluding vendor GPU libraries was decided on 2026-09-26 because they would dominate installer size. |
| APP-007 | The application MUST be free, and Alunan-authored source MUST use Apache-2.0 (selected on 2026-09-26). Third-party code and model weights retain their own licenses, including any use restrictions; the app MUST identify those separately. |

The supported hardware/OS matrix is a release deliverable. Working operating
system graphics drivers remain a machine prerequisite. The installer must not
fetch GPU drivers or development toolkits. Compatibility checks before a large
download must explain unsupported hardware in plain language. Do not advertise
unmeasured Intel Mac, AMD, Intel GPU, or low-memory support. CPU-only generation
is offered only as the explicitly chosen slow mode in GEN-011, never as a
supported or silent default.

MVP scope: lyrics and style to one song; required model preparation; generation
progress and Stop; playback; WAV export; projects and a local results list; model
storage; useful errors, logs, and local help. Advanced score editing, transcription,
reference-audio covers, conversational editing, batch jobs, stems, and DAW/plugin
integration are deferred. Saving a generated score does not imply an MVP score editor.

## 2. The Generate flow

| ID | Requirement |
| --- | --- |
| GEN-001 | The composer MUST offer lyrics, musical style, a tested default model profile, and an optional seed. Explain lyric section tags with a local example. Model/backend terminology belongs in details, not the basic workflow. |
| GEN-002 | Invalid or missing required inputs MUST be identified before network access or model loading. The supported model profile supplies input limits; do not silently truncate user text. |
| GEN-003 | Generate MUST snapshot the submitted inputs, model profile/revision, and source selection. Preparation and generation use that snapshot. Lock generation-affecting inputs while it is active; keep playback, Help, and Logs available. |
| GEN-004 | Check local model readiness first. If files are missing, prepare only the selected operation's dependencies, then continue into generation automatically. The user MUST NOT have to press Generate a second time after downloading. |
| GEN-005 | Before Generate, a missing-model notice MUST describe the one-time download, including any required GPU runtime pack, approximate remaining size when known, automatic continuation, and future reuse. Derive this notice from actual model and runtime readiness, not a first-launch flag. |
| GEN-006 | Permit one active preparation/generation operation per app. Generate becomes Stop throughout preparation, downloading, verification, loading, and generation. Escape invokes Stop while the operation is active. |
| GEN-007 | Progress MUST distinguish checking, downloading, verifying, loading, planning music where applicable, generating audio, and saving the result. Download completion MUST NOT be presented as music completion. |
| GEN-008 | Stop MUST cancel the entire operation, including retry waits and reconnects, and prevent all later stages from starting. Display Stopping until work has actually stopped; retain reusable download bytes. Ignore late events from the cancelled job. |
| GEN-009 | After a stop or failure, retain composer inputs and previous results. A later Generate creates a new snapshot and reuses compatible cached data. Failed or cancelled work MUST NOT be presented or auto-played as a successful new result. |
| GEN-010 | Report success only after a playable audio file and its project metadata are saved. A model that reaches a generation limit MUST produce an explicit incomplete-result warning if audio is retained. An engine's success report is not sufficient: before saving a take as successful, the app MUST check that the audio is finite, not silent, and has the expected format and a plausible duration. Audio that fails these checks is a failed generation, not a take; the error suggests verifying the model files (MOD-011), and the audio is kept only as a diagnostic, never shown or auto-played as a result. |
| GEN-011 | On a machine without a supported GPU backend, the app MAY offer CPU-only generation as a slow mode. The compatibility check MUST say no supported GPU was found and show a measured time estimate before the user chooses it, for example about 15 minutes per minute of audio on a 16-core desktop CPU. The app MUST NOT fall back to the CPU silently when a GPU backend fails to start. Minimum CPU and RAM for this mode are set from measurements before release. |

Suggested first-use copy:

> This song needs a music-model download (about {size}). Alunan saves the files for
> reuse and starts generating automatically when they are ready.

When a GPU runtime pack is also missing, say so in the same notice, for example
"music model and NVIDIA GPU components", with one combined size.

If size is unavailable, say that it is being determined; never invent an estimate.
Once the required files are installed, Generate proceeds locally without this notice.

Normal operation:

`Idle -> Validate -> Check local files -> [Download -> Verify] -> Load ->
[Plan] -> Generate -> Save -> Ready`

Any active stage may enter `Stopping -> Cancelled` or `Failed`. `Waiting to retry`
and `Reconnecting` remain part of preparation. Restarting the application does
not automatically resume a cancelled/crashed generation; it offers the retained
draft and reuses its downloads when the user chooses Generate again.

## 3. Model selection and preparation

| ID | Requirement |
| --- | --- |
| MOD-001 | Ship a curated model catalog and a recommended compatible profile. A profile MUST identify every required generator, decoder, tokenizer/configuration, and license asset, and any GPU runtime pack its backend needs on the current platform; the user must not assemble the pipeline. |
| MOD-002 | Download only the chosen profile's required assets. Alternate quantizations, other languages' separate models, transcription models, and optional capabilities MUST NOT download speculatively. |
| MOD-003 | The catalog MUST pin immutable model revisions and compatible engine versions. An existing project/model MUST NOT silently switch revision, quantization, decoder, backend, or source during a run. |
| MOD-004 | Models MUST be stored persistently in a writable per-user cache outside the installed application. Restarting or upgrading the app MUST preserve them. |
| MOD-005 | A model is ready only when its complete required asset set is accepted. A directory, a weight filename, a 100% transfer meter, or a partially downloaded large file is insufficient evidence. |
| MOD-006 | For app-endorsed downloads, expected SHA-256 digests MUST be anchored in the packaged catalog or a manifest digest pinned by that catalog. Verify newly downloaded files before marking them ready. A failed checksum MUST never become a reusable completed file. |
| MOD-007 | Reuse complete verified files and resume partial files when the source supports byte ranges. Repeated attempts MUST NOT re-download valid completed files. See section 5 for transfer semantics. |
| MOD-008 | A ready model MUST be usable without DNS, HTTP HEAD, manifest refresh, source availability checks, authentication refresh, or another network prerequisite. The engine MUST use local assets and MUST NOT fetch additional dependencies behind the app's back. |
| MOD-009 | Before downloading, check hardware/runtime compatibility, cache/output writability, and disk space for remaining bytes plus required temporary and output storage. Missing models are a normal preparation step. A warning about predicted memory pressure is distinct from a confirmed incompatibility. |
| MOD-010 | If offline with missing files, explain that a one-time download is required, identify what is missing, preserve the draft/partials, and offer Retry when connectivity returns. Installed compatible models and existing audio remain usable. |
| MOD-011 | Settings MUST list model name/profile, local state, size on disk, version, and license, and each installed GPU runtime pack with vendor, version, size, and license. Provide Download without generation, Verify, Remove, and Open models folder. Remove identifies the model or runtime pack and never deletes projects or exported audio. |
| MOD-012 | Support importing a complete compatible model pack from local storage for users preparing an offline machine. Apply the same identity, completeness, and integrity checks as downloading. Never execute code supplied by a model pack. A GPU runtime pack is imported only as the exact vendor archive pinned by the catalog, verified under MOD-015. |
| MOD-013 | Installation and model preparation MUST be distinct. Model preparation may fetch data assets and catalog-pinned vendor GPU runtime packs (MOD-015), but MUST NOT invoke pip, package managers, vendor installers, remote scripts, or separately installed runtimes. |
| MOD-014 | Cache mutations MUST be coordinated across processes. Simultaneous instances must not append to the same partial, delete an in-use model, or expose half-installed files as ready. |
| MOD-015 | When the selected backend needs vendor GPU libraries that the installer omits (NVIDIA cuBLAS for CUDA on Windows and Linux, plus the CUDA runtime on Linux, where the engine links it dynamically), prepare them as a GPU runtime pack. Download only from the vendor's canonical redistributable archive pinned in the packaged catalog by URL, size, and SHA-256; verify the archive before extraction; extract only the catalog-listed files, each with its own SHA-256, into a per-user runtime cache separate from models; and load them only by full path from that verified location. Verify every runtime file's full SHA-256 before each helper launch that loads it. Never run a vendor installer, substitute a same-named library from PATH or the system, or accept runtime code from a model pack. Machines whose backend does not need a pack MUST NOT download one. Show the vendor's license terms with the pack. |

Full verification is required on installation/import, explicit Verify, and after a
known file change or failed load suggesting corruption. Normal ready-model checks
use recorded verification plus local file metadata; hashing gigabytes before every
song is not required. No local receipt makes external files tamper-proof. Explicit
Verify must detect changed contents even when their size is unchanged.

## 4. Download feedback

The behavior below adapts Bunyi's live-byte download experience to music.

| ID | Requirement |
| --- | --- |
| DL-001 | Keep a prominent Downloading music model heading, selected profile, Music generation has not started, and an explanation of automatic continuation visible in the main window, including while viewing earlier results. |
| DL-002 | Show separate Overall model download and Current file meters, filename, percentage to one decimal place when known, readable size, and exact byte counts. Overall completion is byte-weighted across required files, including reusable files and accepted resume prefixes. |
| DL-003 | Count every positive network read. Coalesce visual updates to at most four per second while making a positive receipt visible within 250 ms on an available UI thread, even when rounded percentages do not change. Reused bytes are completion, not network traffic. |
| DL-004 | Show recent download speed, time left to download, elapsed model preparation time, and the age of the last received data. Time left to download MUST NOT be described as time until the song is ready. |
| DL-005 | Unknown totals MUST remain unknown: show Size unknown and actual bytes, without a fabricated percentage or ETA. File and overall totals are resolved independently. |
| DL-006 | After 3 seconds without incoming data, show Waiting for more data. At 30 seconds show Download may be stalled and remove stale speed/ETA. Verification, loading, and intentional retry waits MUST NOT trigger network-stall warnings. |
| DL-007 | Offer Reconnect and resume for a slow or stalled transfer. It replaces the current connection after cancellation completes, preserves valid bytes, keeps the same job active, and automatically continues preparation. Stop takes precedence. |
| DL-008 | Show verification and model loading as separate stages after transfer completion. A next-step explanation MUST make clear that generation follows setup. |
| DL-009 | Keep Stop, Help, and Logs reachable at supported minimum window sizes and display scaling. Label both meters for assistive technology; pace announcements and respect reduced motion. |

Speed and ETA use receipts from the most recent 10 seconds of the current
connection, including quiet time. After at least 30 seconds, show Download is slow
if the last 30-second rate is below 256 KiB/s and more than a minute remains, or
the total is unknown. Waiting/stalled messaging takes precedence; a trickle of
bytes must not erase sustained slowness. Reconnect resets rate history, not the
operation timer. Stop ends that attempt's timer.

Completion measures unique retained data, not cumulative retry traffic or an
average of file percentages. If a server forces a file to restart or verification
rejects data, correct the meter and explain the restart; do not preserve a false
monotonic percentage. At 100% transfer, the model can still be verifying.

GPU runtime pack archives are part of the same preparation job and meters. The
current-file label identifies them as GPU components; archive verification and
extraction are shown as verification, not as network stalls or music progress.

## 5. Download interruption and source recovery

| ID | Requirement |
| --- | --- |
| NET-001 | Write downloads to distinguishable partial files. Stop, connection loss, or app termination MUST preserve useful partial data and completed files for a later attempt. Only verified files are promoted to completed names. |
| NET-002 | Resume only against the same immutable artifact identity. Validate HTTP 206 offsets and total size; never append an HTTP 200 full response to a partial. An ignored range restarts that file only. A 416 response requires local size/digest reconciliation or a bounded file restart. |
| NET-003 | Honor HTTP 429 Retry-After and supported service reset timing, taking the later valid deadline. With no timing, allow up to three retries after 2, 4, and 8 seconds plus up to one second jitter. A required wait over 15 minutes or exhausted retries ends with a clear retry time. |
| NET-004 | Deliberate retry waits MUST show a countdown with Stop available and preserve progress. Retry the canonical source request to obtain a fresh redirect; retain valid range semantics. |
| NET-005 | Service failures, missing required files, and checksum failures MUST be explicit. HTTP 429/503/server errors MUST NOT be reinterpreted as absent manifests, unknown sizes, or a successful partial installation. Do not retry network failures endlessly. |
| NET-006 | A source change MUST be explicit. If an approved alternate exists, explain the change and possible extra download before the user selects it. Otherwise offer Retry without inventing a mirror. Never mix partials across source identities. |
| NET-007 | Keep transient signed redirect URLs separate from model/cache identity. Do not log credentials or complete signed query strings. Downloaded paths MUST remain inside the selected cache; reject traversal, unsafe aliases, and symlink escapes. |

MVP sources are curated in the shipped catalog. The primary source is the
project's model mirror on Cloudflare R2, which hosts the project's own pinned
conversion of the official YuE2 weights with their LICENSE, notices, and a note
of the conversion. Hugging Face is the approved alternate source (NET-006): the
app offers it only through an explicit switch after the mirror fails, and pins
its files separately. Advanced arbitrary repositories and user-configured
sources remain deferred. The mirror is free and non-commercial, as the weight
license requires.
Bunyi's production model URLs and credentials are not Alunan defaults.

## 6. Results, projects, and privacy

| ID | Requirement |
| --- | --- |
| OUT-001 | Provide play/pause, seek, elapsed/duration display, and WAV export using bundled/platform audio support. Final sample rate/channel information MUST describe the actual saved audio. |
| OUT-002 | Save projects with inputs, seed, model/decoder identity, quantization, engine version, effective settings, generated score when available, result status, and relative audio paths. Preserve earlier takes when generating a new one. |
| OUT-003 | A copied project MUST open and play on every platform without the original model cache. Re-generation may require a compatible model download. Different backends are not required to produce bit-identical audio from a seed. |
| OUT-004 | Never overwrite an existing take implicitly. Failed saves MUST identify the failure and MUST NOT create a successful results-list entry. |
| OUT-005 | Model removal, source changes, app upgrades, and ordinary uninstall MUST preserve projects and exported audio. Model deletion is a separate explicit storage action. |
| UX-001 | Errors MUST explain the affected stage and a useful next action while preserving user work. Developer diagnostics are available in Logs; internal tensor/kernel details are not the primary error message. |
| UX-002 | Provide local help for model setup, offline operation, supported hardware, lyric structure, storage, and recovery. Help MUST work while disconnected or busy. |
| UX-003 | Support keyboard operation, native accessibility APIs, readable scaling, and native file dialogs. Match feature behavior across platforms without forcing identical layouts. |
| UX-004 | Show application, dependency, engine, and model credits/licenses. Do not imply that the application's open-source license replaces YuE2 weight restrictions. |
| UX-005 | Before the first model download, the app MUST show a short summary of the model terms (CC BY-NC 4.0, the individual creator permission to monetize outputs, that company commercial use needs a separate license, and the responsible-use conditions) with a link to the full terms, and record a one-time acknowledgement. Declining cancels preparation and keeps the draft. The terms remain available in model settings and credits. |

Closing the app during work stops and cleans up its helper before exit, retaining
partial downloads and the saved draft. The OS may forcibly terminate the app;
next launch must recognize interrupted files/jobs instead of claiming success.
External license/source links open only on user action. Model downloading sends
only asset requests, not the song's lyrics/style/score or generated audio.

## 7. Acceptance scenarios and platform parity

These are release checks to implement later, not claims of tests already run.
Automated transfer/contract tests complement real clean-machine, GPU, and native
accessibility testing. Successful compilation alone does not establish parity.

| Scenario | Requirement coverage | Expected result |
| --- | --- | --- |
| AC-001 Clean install | APP-001..006 | Install with no developer runtimes present. App opens without a terminal, extra setup, model download, or GPU runtime download. |
| AC-002 First song | GEN-001..007, MOD-001..005, MOD-015, UX-005 | Generate with valid inputs and an empty cache shows the one-time model-terms acknowledgement, then downloads only required assets, including a GPU runtime pack only where the backend needs one, then generates automatically. |
| AC-003 Offline reuse | APP-004, MOD-008 | With a ready model and any required runtime pack, deny all network access. Generate, save, play, and export succeed; no model-source or vendor request is attempted. |
| AC-004 Offline first use | MOD-010, GEN-009 | Empty cache while offline gives useful recovery and preserves inputs. No cloud inference fallback occurs. |
| AC-005 Stop/resume | GEN-008..009, MOD-007, NET-001..002 | Stop midway through a large file, restart the app, and Generate. Valid files are skipped and a supported range resumes exactly. |
| AC-006 Range edge cases | NET-002 | Exercise valid/invalid 206, ignored Range/200, 416, and changed source identity. No duplicated, mixed, or falsely complete bytes. |
| AC-007 Integrity | MOD-005..006, NET-005 | Missing decoder/config, truncated weights, wrong digest, and same-size corruption fail verification and cannot be loaded as ready. |
| AC-008 Progress accounting | DL-001..005 | Mix a large file, small files, cached files, one-byte reads, retry traffic, and unknown totals. Meters and receipts remain truthful. |
| AC-009 Slow/stalled connection | DL-004..008 | Simulated quiet periods, trickle transfers, verification, and reconnects produce the specified health/ETA states. Stop cancels recovery. |
| AC-010 Rate limits/service failure | NET-003..006 | Honor retry timing, stop during waits, cap retries, preserve bytes, and never disguise 429/503 as missing metadata. |
| AC-011 Preflight | GEN-002, MOD-009 | Bad inputs, unwritable paths, confirmed incompatibility, or insufficient storage are caught before large transfers. |
| AC-012 Crash and stale events | APP-003, GEN-008..010, NET-001 | Kill the helper/app during download, generation, and save. Recover draft/cache; no orphan helper, late success, or stale playback. |
| AC-013 Project portability | OUT-001..004 | Open and play a project on each OS without its model cache. Re-generation clearly prepares a compatible profile when needed. |
| AC-014 Storage lifecycle | MOD-004, MOD-011..015, OUT-005 | Upgrade, Verify, Remove, local import, and simultaneous app instances preserve projects and cache correctness. |
| AC-015 Native usability | APP-007, DL-009, UX-001..005 | Keyboard/screen-reader use and display scaling keep progress, Stop, recovery, Help, and license information usable. Credits identify Alunan's Apache-2.0 source license separately from dependency and model terms. |
| AC-016 Full-song quality | GEN-007, GEN-010, OUT-002..003 | Real hardware produces audible songs, reports truncation honestly, and records the engine/model settings used. An engine run that reports success but yields silent or non-finite audio (for example with same-size corrupted decoder weights) ends as a failure with a Verify suggestion, and no take is added. |
| AC-017 GPU runtime pack | MOD-012..013, MOD-015 | Wrong archive digest, extra or traversal archive entries, a tampered same-size runtime file, and a same-named library planted in PATH, the app folder, or the working directory are rejected or never loaded. Importing the pinned vendor archive offline works. A machine whose backend needs no pack downloads none. |
| AC-018 No-GPU slow mode | GEN-011, MOD-009 | On a machine without a supported GPU (and a GPU driver that fails to initialize), the app states that no supported GPU was found and shows the measured estimate before any CPU generation; nothing runs on the CPU without the user's choice. |

| Feature group | Windows / WinForms | Linux / GTK 4 | macOS / Swift |
| --- | --- | --- | --- |
| Standalone package and managed helper | Required; planned | Required; planned | Required; planned |
| On-demand downloads and offline reuse | Required; planned | Required; planned | Required; planned |
| Progress, Stop, recovery, integrity | Required; planned | Required; planned | Required; planned |
| Generation, playback, projects, export | Required; planned | Required; planned | Required; planned |
| Model settings, local help, accessibility | Required; planned | Required; planned | Required; planned |
| GPU runtime pack (MOD-015) | Required for CUDA; planned | Required for CUDA; planned | Not expected: Metal is part of macOS; confirm with the selected backend |

Permitted differences: native layout, OS storage locations, accessibility API,
GPU backend, engine-specific model format, and whether a GPU runtime pack is
needed. Supported profiles may differ after measurement. Such differences must be
recorded before release, with a user-visible capability explanation; they do not
waive core feature behavior.
