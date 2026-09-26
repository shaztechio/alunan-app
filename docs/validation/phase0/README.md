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
No system build tools were installed during initial inspection. Finding toolkit
folders alone does not verify a working compiler or a redistributable package.
For the C++ candidate, the user approved installing VS 2022 Build Tools (C++
workload, MSVC 14.44.35207, Windows SDK 10.0.26100) on 2026-09-26. CMake 4.4.3
and Ninja 1.13.2 are pip packages in ignored `.phase0/build-tools-venv`, not PATH.

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
| Windows C++ CUDA build (sm_89) | Passed | [Build record](windows-cpp-build.json): pinned commit/submodule, no patches, binary hashes and DLL imports; cuBLAS/cuBLASLt (516 MB) needed at run time, to be downloaded from NVIDIA as a GPU runtime pack (decision 2026-09-26) |
| Windows C++ Q8, short fixture in two processes | Passed technical checks; listening pending | [Report](windows-short-cpp-q8.json): 66.359 s of audio in 14.35 s per process; identical WAV hashes across processes; no truncation |
| Windows C++ Q8, full fixture | Passed technical checks; listening pending | [Report](windows-full-cpp-q8.json): 169.839 s of audio in 37.68 s; no truncation; 3 float samples exceed full scale (peak 1.072) |
| Q8 acoustic-stage parity vs Python float32 | Passed (informational) | [Report](windows-q8-nar-cossim.json): upstream harness; final latent cosine 0.999888, decoded audio STFT cosine 0.999957 |
| C++ Metal compilation and inference | Not run | No Mac |
| AR (LM) logit parity | Not run | Upstream LM harness targets a BF16 GGUF outside the pinned profile |
| Blind listening, reference vs C++ Q8 (Windows) | Recorded; one reviewer | [Review](windows-listening-review-1.json): all four takes pass overall; C++ candidate preferred for short and full; one distorted take per engine; small sample with listed blinding limits |
| Pinned NVIDIA cuBLAS runtime pack (Windows) | Passed | [Record](windows-runtime-pack.json): archive matched pinned size/SHA-256; allow-listed DLLs identical to the tested toolkit copies and NVIDIA-signed; short fixture with no toolkit on PATH loaded cuBLAS only from the pack and reproduced the WAV hash |
| C++ forced termination per stage | Passed | [Record](windows-cpp-termination.json): exit within 80 ms and device GPU memory back to baseline within 140 ms at load/score/semantic/acoustic/decode; no leftover files; final write phase not probed |
| C++ kill during final write | Failure mode confirmed | [Record](windows-cpp-final-write.json): a kill mid-write left a WAV 556 bytes short that still parses and plays; kills after writing exit 1 with complete files. Worker must stage and promote outputs |
| C++ repeated full jobs (5 processes) | Passed | [Record](windows-full-cpp-q8-repeat5.json): 37.4-38.3 s each, identical WAVs, flat RSS/GPU peaks, same idle GPU baseline before every job |
| C++ multi-architecture CUDA build | Built; RTX 4090 only exercised | [Record](windows-cpp-multiarch.json): sm_75/86/89/120a + compute_120a; ggml-cuda.dll 103.7 MB vs 51.6 MB; identical WAV on the 4090; other architectures untested |
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

## C++ CUDA candidate on Windows (2026-09-26)

`yue-synth` was built from a detached checkout of the pinned yue2.cpp commit and
GGML submodule with `GGML_NATIVE=OFF`, architecture 89, CUDA 13.3.73 and MSVC
19.44. No source was patched. The embedded version is the upstream `f17d526`,
not Alunan's commit. `tools/phase0/run-cpp.py` converted each fixture using the
recorded recipe: same style, lyrics, `cot` and seed for both `lm_seed` and `seed`,
32 steps, one song, `wav32`, 360 s budget. `yue-server` was never started.

| Measurement (RTX 4090) | Python eager BF16 reference | C++ Q8_0 + F32 VAE |
| --- | ---: | ---: |
| Short: audio / generation time | 78.959 s / 113.857 s | 66.359 s / 14.35 s (whole process) |
| Short: peak process RSS | 9.04 GiB | 2.29 GiB |
| Short: peak GPU | 10.29 GiB reserved (PyTorch allocator) | 5.23 GiB device-wide above idle baseline |
| Full: audio / generation time | 166.119 s / 262.795 s | 169.839 s / 37.68 s (whole process) |
| Full: peak process RSS | 9.18 GiB | 2.36 GiB |
| Full: peak GPU | 19.76 GiB reserved | 5.36 GiB device-wide above idle baseline |
| Repeat determinism | Identical decoded samples in one process | Identical WAV hash across two processes |

C++ times include process start, model load and WAV write; reference times
exclude pipeline initialization, so the comparison slightly favors the
reference. The GPU columns use different instruments (allocator vs
`nvidia-smi` device-wide) and are indicative only. Q8 weights plus the F32 VAE
are 4.34 GB against 7.79 GB for the reference profile. OS caches were not
flushed. The engine loads one model half at a time (strict store policy).

The engines sample differently, so the WAVs are different renditions of the same
request and must be compared by listening, not by hash. The full C++ take has
three float samples above 1.0 (peak 1.072) whereas the reference peaked at 1.0;
a 16/24-bit export path must limit or clip explicitly. `yue-synth` reports
per-stage truncation on stderr; neither stage was truncated.

Upstream's `debug-nar-cossim.py` ran unmodified on CUDA with Q8_0, sharing the
AR sequence and noise between GGML and the float32 Python reference built from
the verified official checkpoint. Latent cosine stays above 0.99988 over 32
steps; decoded audio STFT cosine is 0.999957, matching upstream's published
Blackwell values to about 1e-5. This isolates prefill, flow matching and decoding;
it does not validate AR sampling, which differs by design. The LM logit harness
was not run because it needs a BF16 GGUF outside the pinned candidate profile.

The first runner attempt failed before inference because it passed relative
paths to a child running in another directory; that runner defect was fixed and
its output kept as `.phase0/runs/windows-short-cpp-q8-relative-path-runner-bug`.

These results do not select a production backend. Follow-up results are below.
Remaining for this candidate: blind listening against the reference, a clean
machine without the VC++ redistributable, full-path runtime-pack loading in a
worker, CUDA architecture coverage on real non-Ada GPUs, and native Linux builds.

## Runtime pack, termination, and CUDA architectures (2026-09-26)

**cuBLAS runtime pack.** The pinned NVIDIA archive (393,706,755 bytes) matched
its pinned SHA-256. Its 25 entries had no unsafe paths; extracting only
`cublas64_13.dll`, `cublasLt64_13.dll` and `LICENSE` produced DLLs byte-identical
to the toolkit copies the tested binaries used, each with a valid NVIDIA
Authenticode signature. The short fixture then ran with PATH reduced to the pack
folder and Windows system folders and `CUDA_PATH` removed: no toolkit DLL was
mapped, cuBLAS came from the pack, and the WAV hash matched the earlier run. The
MSVC runtime and OpenMP came from System32, because this machine has the VC++
14.51 redistributable; a clean machine remains untested. PATH isolation is
weaker than MOD-015's full-path loading: the executable folder and System32 are
searched first, so the Phase 3 worker must set its DLL search directories itself.

The archive's bundled NVIDIA license lists the CUDA BLAS library as
distributable with applications and requires that distributable portions be
accessed only by the application. Whether an app-initiated end-user download
from NVIDIA fits that grant is recorded as an open review question, not decided.

**Forced termination.** `yue-synth` has no cancellation channel. Killing it with
`TerminateProcess` after model load started, during score and semantic
generation, during flow matching, and at decode exited within 80 ms each time.
Device GPU memory returned to baseline within 140 ms and no compute process
remained. No output files existed, because outputs are written only after
decoding. The final write phase writes directly to target paths and was not
probed; the worker must write to temporary names and promote afterwards.

**CUDA architectures.** A build for `75-real;86-real;89-real;120-real;120-virtual`
took 509 s and doubled `ggml-cuda.dll` to 103.7 MB (+52 MB, small beside cuBLAS).
On the RTX 4090 it produced the identical WAV in 14.69 s versus 14.35 s. ggml
rewrote 120 to the architecture-specific `120a`, so its PTX is not a generic
fallback for later GPU generations. Turing, Ampere and Blackwell code was
compiled but never executed here. The supported-GPU list must come from
measurements on those GPUs, not from the build list.

**Final write and repeated jobs.** `yue-synth` writes its five outputs about
40-80 ms after the decoder unloads. Killing it inside that window left, in
different trials, an empty `tokens.csv`, earlier files without the WAV, or a WAV
556 bytes (70 frames) short that libsndfile parses without error while its
header still declares the full size. Kills just after writing returned exit code 1
with every file complete. Success must therefore come from the worker's explicit
terminal message after a clean exit, with outputs staged under temporary names
and promoted afterwards, never from file presence or parsing. Five consecutive
full-song processes then ran in 37.4-38.3 s each with identical WAVs, flat memory
peaks, and the same idle GPU baseline before each job. A long-lived worker that
keeps models loaded between jobs has not been tested.

**Listening review.** `tools/phase0/make-listening-kit.py` wrote blind A/B pairs
of the retained short and full takes through one WAV writer with equal
timestamps, a scoring sheet, and a separate key. The project owner listened on
speakers and rated all four takes pass overall, preferring the C++ Q8 candidate
for both fixtures. Audible distortion was reported in the reference short take,
which has no near-full-scale samples, and in the C++ full take, whose three
over-full-scale samples near 141 s and 144 s are unlikely to explain it alone.
This is one reviewer and one take per engine; engine and A/B position were
confounded by the random draw, durations differ, and a question asked with the
preferences mentioned the C++ overs. It supports keeping the candidate, not a
final quality bar.

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
| P0-02 | Source/model pins, Windows Python distribution hashes, and Windows C++ CUDA build/binary hashes recorded | Build-tool lock, Linux/Mac builds, tested profiles for all targets |
| P0-03 | Windows reference and C++ Q8 short/repeated/full technical runs passed; Q8 acoustic-stage parity and a first blind listening review recorded | Outputs on other targets; AR parity where applicable; broader listening (more takes/reviewers) and other targets |
| P0-04 | Timing/memory/output/repeat reports, reference callback probes, C++ per-stage and final-write termination, and five repeated C++ full jobs recorded | Cold caches/temp peaks, out-of-memory and missing/corrupt asset failures; agree on quality and latency |
| P0-05 | Metal-first evaluation order and MPS correctness issue documented | Real Mac Metal test, then measured alternatives only if necessary |
| P0-06 | [Preliminary dependency/license inventory](dependencies.md); user selected Apache-2.0, applied in LICENSE; cuBLAS pack pinned and verified | Tokenizer terms, NVIDIA end-user download review, approved distribution origins and exact bundled-component notices |
| P0-07 | .NET 10, Gir.Core 0.8.1 and candidate OS/package baselines recorded | Validate GTK closure/API floor, Mac SDK, and clean-machine packaging path |

All Phase 0 checklist items remain open because each includes work beyond this
initial evidence. Phase 1 remains unstarted. No unavailable target is waived and
the three-native-platform/local-generation scope is unchanged.

Next work, by what it needs:

- A human reviewer, later: more takes and reviewers once other targets produce
  audio; the first Windows review is recorded.
- A licensing decision: NVIDIA's terms for app-initiated cuBLAS downloads.
- Other hardware: a clean Windows machine without the VC++ redistributable;
  Turing/Ampere/Blackwell GPUs for architecture coverage; native Linux; Apple
  Silicon for Metal. None of these can be counted as passing until run.
- Here, independently: cold-cache startup and peak temporary disk, and the
  engine's behavior with missing or corrupt model files and out-of-memory
  conditions. Native Linux and Apple Silicon hardware validation remain
  explicit open gates.
