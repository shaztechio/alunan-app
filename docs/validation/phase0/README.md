# Phase 0 feasibility evidence

Date: 2026-09-26. Status: **in progress; exit gate not met**.

This is a record of actual observations, with unrun work kept explicit. It does
not qualify a native app, installer, or supported hardware minimum. See the
[engine decision record](../../decisions/0001-engine-feasibility.md) for evaluation
order and the [shared spec](../../../spec/FEATURES.md) for product promises.

## Hardware and tool access

| Target | Evidence | Status |
| --- | --- | --- |
| Windows x64 | Windows 11 Pro 10.0.26200; RTX 4090; 24,564 MiB reported VRAM; driver 617.14; compute capability 8.9; 101,960,773,632 bytes system RAM | Reference short/repeated/full technical checks passed; listening and packaging pending |
| Linux auxiliary environment | Ubuntu 24.04.2 under WSL2; kernel 6.18.33.2-microsoft-standard-WSL2; same GPU/driver visible | Hardware visibility passed; no generation run; not native Linux release evidence |
| Native Linux | No native Linux test host verified in this task | Not run |
| macOS Apple Silicon | User explicitly confirmed no Mac available yet | Not run; needs hardware |

About 382.7 GB was free on the workspace volume at initial inspection. Windows
has .NET SDK 10.0.401, Python 3.12.9, and CUDA toolkit directories 13.0/13.3.
No CMake/Ninja/MSVC installation was found in PATH or standard Visual Studio
locations. WSL did not expose CMake, Ninja, g++, nvcc, or uv through PATH.
No system build tools were installed by this investigation. Finding toolkit
folders alone does not verify a working compiler or a redistributable package.

## Evidence ledger

| Check | Result | Evidence / limitation |
| --- | --- | --- |
| Pinned source archives | Passed | Four archive SHA-256 values in [source pins](source-pins.json), including the exact GGML submodule |
| Candidate model identity | Passed for research | [Two candidate profiles](model-profiles.lock.json); every required file has immutable URL, size, SHA-256 |
| Official model preparation | Passed | All 17 reference assets downloaded and checked locally; 7,794,565,436 total bytes |
| Interrupted transfer recovery | Observed successful recovery | Initial generator transfer ended early at 3,255,258,007 bytes; PowerShell resume stalled; bounded curl range recovery completed; whole-file SHA-256 then matched |
| Reference dependencies | Passed | `pip check`; torch 2.10.0+cu128 detects RTX 4090; YuE2 imports. [31 distribution artifacts](windows-python-packages.lock.json) recorded |
| Relocated reference venv recreation | Passed | Rebuilt in `alunan-app` from the hash lock with `--require-hashes --no-deps`; `pip check` passed; all 14 installed modules matched the source record; RTX 4090 visible; 4,881,476,240 bytes. The incomplete 250 MB copy is retained as `.phase0/reference-venv-copied-unqualified` |
| Windows default `torch` backend | Failed | [Failure report](windows-default-failure.json): `USE_FLASH_ATTENTION was not enabled for build.` at CUDA graph decode; no audio result |
| Windows `torch-eager`, short fixture twice | Passed technical checks; listening pending | [Report](windows-short-eager.json): both runs complete, finite/non-silent 48 kHz stereo; no truncation; no Python network attempts |
| Windows `torch-eager`, full fixture | Passed technical checks; listening pending | [Report](windows-full-eager.json): 166.119 s of audio in 262.795 s; no truncation or Python network attempts |
| Windows upstream cancellation callbacks | Four interruption probes passed; limitations found | [Report](windows-cancellation.json): pre-cancel still loads model; small CUDA allocations persist after in-process close; decoder has no cancellation callback |
| C++ CUDA/Metal compilation and inference | Not run | Build toolchains unavailable here; no Mac |
| Official-vs-C++ stage parity/listening | Not run | Needs built candidate and outputs from both paths |
| Standalone packaging | Not run | Current Python venv is a developer environment; no clean-machine package tested |

The successful transfer recovery is not an app acceptance test. The research
script does not implement the full download state machine or range edge-case
suite from the feature spec. The GGUF weights have not been downloaded; their
large-file digests are upstream LFS metadata, not local content verification.
The lock's `digestEvidence` describes the initial pinning observation; subsequent
reference-file verification is recorded here without changing the frozen lock.

## Initial Windows measurements

The eager backend is upstream's `torch-eager` option. No YuE2 source patch was
needed. [All 14 installed Python modules](reference-source-verification.json)
matched the inspected source archive; the same record pins the benchmark script.

| Short fixture measurement | First run | Same-process repeat |
| --- | ---: | ---: |
| Generated audio | 78.959 s | 78.959 s |
| Generation, including stage loads | 113.857 s | 113.245 s |
| Sampled peak process RSS | 9.04 GiB | 9.03 GiB |
| Peak PyTorch CUDA reserved | 10.29 GiB | 10.55 GiB |
| Process RSS after saving | 9.09 GiB | 8.93 GiB |
| Truncation | None reported | None reported |

The complete two-run process took 239.37 seconds, including local verification,
imports, pipeline initialization and saves. A separate first-process run is
needed for startup comparisons; no OS cache was flushed. Two repetitions do not
establish absence of a slow leak. [Numerical comparison](windows-short-repeat-comparison.json)
found identical decoded samples. WAV file hashes differ because container bytes
can differ; there is no claim of cross-platform seed equivalence.

The installed research venv occupied 4,881,443,273 bytes when measured, separate
from the 7.79 GB model cache and package-manager/source caches. This is not a
compressed installer size. Peak temporary disk usage was not instrumented.

The full fixture produced **166.119 seconds** of audio in **262.795 seconds**
(274.717 seconds for the whole benchmark process). It passed the same 48 kHz
stereo, finite/non-silent and non-truncated checks. Sampled process RSS peaked at
9.18 GiB; CUDA allocator peaks were 13.68 GiB allocated and 19.76 GiB reserved.
Output artifacts occupied 96,378,389 bytes. The larger GPU reservation shows why
short-run memory cannot establish the full-song hardware minimum.

All three WAV hashes were rechecked against the saved reports. Actual WAVs,
scores, semantic tokens, latents and effective generation settings remain in
ignored `.phase0/runs/windows-short-eager/` and `.phase0/runs/windows-full-eager/`.
They are retained for C++ comparisons and listening; no listening score has been
assigned. These developer reference runs do not establish a packaged Windows
backend or complete AC-016.

## Cancellation follow-up (2026-09-26)

Four new probes used the same verified models/source and the retained short-song
plan/semantic tokens; completed music benchmarks were not repeated. Each raised
the expected `InterruptedError`. No Python network attempts were observed.

| Boundary | Observed request-to-exception delay | CUDA allocated / reserved after close and collection |
| --- | ---: | ---: |
| Already cancelled before planning call | 5.953 s | 0 / 0 bytes |
| Planning after eight output tokens | 0.027 s | 8,519,680 / 20,971,520 bytes |
| Semantic generation after eight output tokens | 0.028 s | 8,519,680 / 20,971,520 bytes |
| Acoustic synthesis at its third cancellation check | 0.000118 s | 9,568,256 / 23,068,672 bytes |

These synthetic callbacks test interruption propagation, not worst-case external
Stop latency. In particular, the acoustic flag is raised at an existing polling
point after a half-step; the near-zero delay excludes the wait to reach that
point. Cleanup duration was not measured, and the remaining allocations do not
by themselves establish a leak. The probe process exited normally afterward.

Integration findings: upstream `plan()` loads the generator before its first
cancellation check, so the coordinator must reject cancelled work before model
load. The pinned `decode()` method accepts no cancellation callback and performs
model transfer/load and tiled VAE decode synchronously. A responsive control
channel plus bounded worker termination, or a tested engine patch, is still
required for Stop during those stages. These probes do not complete AC-011/012
or validate application supervision. No upstream code was patched.

## Reproduction and measurement

[Developer commands and benchmark protocol](../../../tools/phase0/README.md)
describe the isolated environment, exact assets, fixed original lyric fixtures,
offline guard, C++ build recipe, and listening/failure checks still required.
No upstream demo audio was downloaded or used as evidence of local generation.

Reports preserve failed runs. A successful technical smoke requires a finite,
non-silent, non-truncated 48 kHz stereo WAV and saved artifacts. This checks
format and completion, not musical quality; listening remains separately recorded.
The same-process repeat tests reuse a pipeline. OS file caches are not flushed,
so first-process startup must not be labeled a measured disk-cold start.

Memory accounting initially uses 100 ms process RSS samples and PyTorch CUDA
allocator peaks. Neither is a complete whole-machine/driver memory measurement.
Python audit hooks reject socket-connect/DNS requests during generation; they
do not establish that native libraries cannot contact a network. A later
OS-denied network test is required for release AC-003/AC-016.

## Phase task status and remaining gates

| Task | Progress | Required before completion |
| --- | --- | --- |
| P0-01 | Candidate targets and current host recorded | Obtain native Linux and Apple Silicon test access |
| P0-02 | Source/model pins and Windows Python distribution hashes recorded | C++ build/toolchain closure, binary hashes, tested profiles for all targets |
| P0-03 | Windows eager reference short/repeated/full technical runs passed; default backend failure preserved | Outputs on other targets; reference/candidate stage and listening comparisons |
| P0-04 | Timing/memory/output/repeat reports and four callback interruption probes recorded | Measure external-stop/cleanup deadlines, cold caches/temp peaks and remaining failures; agree on quality and latency |
| P0-05 | Metal-first evaluation order and MPS correctness issue documented | Real Mac Metal test, then measured alternatives only if necessary |
| P0-06 | [Preliminary dependency/license inventory](dependencies.md); user selected Apache-2.0, applied in LICENSE | Tokenizer terms, approved distribution origins and exact bundled-component notices |
| P0-07 | .NET 10, Gir.Core 0.8.1 and candidate OS/package baselines recorded | Validate GTK closure/API floor, Mac SDK, and clean-machine packaging path |

All Phase 0 checklist items remain open because each includes work beyond this
initial evidence. Phase 1 remains unstarted. No unavailable target is waived and
the three-native-platform/local-generation scope is unchanged.

Next independent work: obtain/configure a C++ developer toolchain, build the
pinned C++/GGML CUDA candidate, and compare it against these saved reference
outputs. Then measure cancellation/failures and packaging closure. Native Linux
and Apple Silicon hardware validation remain explicit open gates.
