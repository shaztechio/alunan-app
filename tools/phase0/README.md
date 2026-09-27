# Phase 0 developer tools

These tools run research experiments. They are not installers, app setup steps,
the production model downloader, or the future worker protocol. Model/source
archives, environments, and results live under ignored `.phase0/`.

## Recorded Windows reference setup

The inspected host has Python 3.12.9, .NET SDK 10.0.401, an RTX 4090, and a working
NVIDIA driver. Source identities/archive hashes are in
[`source-pins.json`](../../docs/validation/phase0/source-pins.json). Download the
official source archive at that exact revision, verify its SHA-256, and extract
it under `.phase0/yue2/` before using the commands below.

```powershell
python -m venv .phase0/reference-venv
& .phase0/reference-venv/Scripts/python.exe -m pip install --index-url https://download.pytorch.org/whl/cu128 torch==2.10.0 --report .phase0/torch-install-report.json
$taskSource = (Get-ChildItem .phase0/yue2 -Directory).FullName
& .phase0/reference-venv/Scripts/python.exe -m pip install $taskSource --report .phase0/reference-install-report.json
& .phase0/reference-venv/Scripts/python.exe -m pip check
& .phase0/reference-venv/Scripts/python.exe tools/phase0/validate-locks.py
```

Those commands describe the observed setup; rerunning unconstrained pip can
resolve newer transitive dependencies. For an exact repeat, use the recorded
distribution URLs/SHA-256 values in
[`windows-python-packages.lock.json`](../../docs/validation/phase0/windows-python-packages.lock.json)
and install those verified wheels without dependency resolution, then install the
YuE2 source with `--no-deps`. `install-reference-venv.py` does this and refuses to
reuse an existing venv directory:

```powershell
python tools/phase0/install-reference-venv.py
``` Build tooling also needs a lock before release.

Prepare only one model profile. The reference requires 7.79 GB of model data;
leave additional space for the several-GB environment, package cache and results.
The script verifies every cached/downloaded file. It retains partials and uses
PowerShell's range resume, but has no automatic retry loop or production UI.

```powershell
./tools/phase0/prepare-models.ps1 -Profile yue2-reference-bf16
```

If the host drops a large transfer, retain the partial. On the investigated host,
PowerShell resume stalled; a bounded `curl --continue-at -` against the same pinned
URL completed it. Rerun preparation to verify/promote the full-size partial. This
is research-only recovery, not a tested implementation of AC-005/AC-006.

Run with a new output directory each time (the runner rejects overwrites):

```powershell
& .phase0/reference-venv/Scripts/python.exe tools/phase0/run-reference.py --request tools/phase0/requests/short.json --output .phase0/runs/short --backend torch-eager --repeat 2
& .phase0/reference-venv/Scripts/python.exe tools/phase0/run-reference.py --request tools/phase0/requests/full.json --output .phase0/runs/full --backend torch-eager
```

The default `torch` backend is deliberately selectable to reproduce the recorded
Windows flash-attention failure. The eager option is an upstream backend, not an
unrecorded patch. No automatic fallback occurs in this runner.

The runner verifies local files before loading, sets offline environment flags,
and blocks Python socket-connect/DNS audit events. It writes a report even when
inference fails, checks finite/non-silent 48 kHz stereo WAV output, records
truncation, and keeps the source artifacts. This is not OS-wide network denial,
an audio listening review, or a clean-machine packaging check.

## C++ candidate build recipe (executed on Windows 2026-09-26)

Use a detached checkout at the recorded C++ commit and its pinned GGML submodule;
check both before building. Avoid a bare source archive inheriting Lagu's Git
identity through the upstream version-generation script. MSVC C++ Build Tools,
CMake, and the CUDA build toolkit are developer requirements. They are not user
installation requirements for Lagu.

From a configured developer environment, configure with `GGML_CUDA=ON`,
`GGML_NATIVE=OFF`, and an explicit tested architecture list (89 for the local
RTX 4090 experiment). Build the `yue-synth` target. Record compiler/CMake/CUDA
versions, flags, binary hashes, DLL/SO imports, and any patches. Do not treat a
local architecture-89 build as suitable for every NVIDIA GPU.

Prepare `yue2-cpp-q8` only when a runnable candidate is available. Convert the
fixed request into the C++ schema: copy style/lyrics/cot, set both `lm_seed` and
`seed` to the fixture seed, keep 32 ODE steps, one song/variation, `output_format`
`wav32`, and the normal 360-second semantic budget. Record every effective
setting; remove the reference-only `id`. Use `yue-synth --model ... --vae ...
--request ... --out ... --score ... --tokens ... --latent ...`. Never start
`yue-server` for this experiment.

Compare intermediate BPE/AR/NAR/VAE results using upstream parity tools where
compatible; float/quantized output is not expected to be byte-identical. Preserve
the same decoder and distinguish any sampling/backend differences in the report.

Windows commands used (from the repository root, after a detached clone at the
pinned commit into `.phase0/yue2-cpp-git` with `git submodule update --init`, and
`python -m venv .phase0/build-tools-venv` plus `pip install cmake ninja`):

```powershell
cmd /c tools\phase0\build-yue2-cpp.cmd
./tools/phase0/prepare-models.ps1 -Profile yue2-cpp-q8
& .phase0/reference-venv/Scripts/python.exe tools/phase0/run-cpp.py --request tools/phase0/requests/short.json --output .phase0/runs/short-cpp --repeat 2
& .phase0/reference-venv/Scripts/python.exe tools/phase0/run-cpp.py --request tools/phase0/requests/full.json --output .phase0/runs/full-cpp
```

`build-yue2-cpp.cmd` takes an optional architecture list and build name, for
example `"75-real;86-real;89-real;120-real;120-virtual" yue2-cpp-build-cuda-multi`.

`run-cpp.py` verifies binary and model hashes, writes the converted request,
runs each repeat as a new `yue-synth` process, samples process RSS and
device-wide GPU memory, and applies the same WAV checks as the reference runner.
For upstream's `tests/debug-nar-cossim.py`, the checkout needs `build/` (with an
extensionless `yue-synth` hard link on Windows), `models/`, and `checkpoints/`
hard-linked to verified files, plus `modeling_vae.py` from the installed package.

`run-cpp.py --runtime-dir <folder>` reduces the child's PATH to that folder and
the Windows system folders, removes `CUDA_PATH*`, and records every DLL the
process maps. It tests a runtime pack without the toolkit; it is not the
full-path loading MOD-015 requires of the app.

`probe-cpp-termination.py <new-report.json>` kills `yue-synth` at five stage
markers and records exit latency, device GPU release, and leftover files.
With `--final-write [--delays 44,48,...]` it instead kills at delays after the
decoder unloads and records which outputs exist, their sizes, and whether a
partial WAV parses.

`probe-cpp-cold-start.py <new-report.json>` copies the pinned GGUFs with
unbuffered I/O, runs a cold and a warm short job, and records stage load times,
process I/O, and new TEMP files. `probe-cpp-failures.py <new-report.json>` runs
missing, truncated, corrupted, and wrong model files from scratch copies, then
the short job with a helper holding VRAM (`--keep-free-mib`). Both delete their
scratch copies.

`build-yue2-cpp-runtime-proto.cmd` builds the pinned engine with
`patches/yue-synth-gpu-runtime-dir.patch` applied to a copy of the source
(`.phase0/yue2-cpp-proto-src`) and cuBLAS delay-loaded.
`probe-runtime-loading.py <new-report.json>` then runs it with and without
`ALUNAN_GPU_RUNTIME_DIR`, with fake cuBLAS DLLs planted in the app folder,
working directory and PATH, and records which cuBLAS files were mapped.

`make-listening-kit.py` writes a blind A/B kit of the retained reference and C++
takes to `.phase0/listening/kit-1` with a scoring sheet and a separate key.

## Benchmark completion criteria

For each real target: record exact OS/driver/hardware, revisions, hashes, settings,
first-process and repeated same-process timing, stage timing, process and GPU
memory scope, cache and peak temporary/output space, and output duration. Separate
an OS cold-cache measurement from a first-process measurement.

Listen to short/full pairs for intelligibility, lyric completion/order, consistent
voice, clipping/noise, coherent structure and ending, and style adherence. Record
reviewer/date and severity (pass/minor/major/fail); blind the engine labels where
practical. Retain any truncation as a failure to complete that fixture. Agree on
quality/latency targets after collecting the results, not from upstream claims.

Then test repeated full jobs, out-of-memory handling, cancellation during each
stage, missing/corrupt assets, unwritable output and worker termination. These
remain separate evidence from the initial smoke runs. Test packaged offline
generation with OS network denial later; Python audit hooks alone cannot qualify
AC-003 or AC-016.

## Reference cancellation probes

After retaining the short benchmark's first take, run:

```powershell
& .phase0/reference-venv/Scripts/python.exe tools/phase0/check-cancellation.py .phase0/runs/windows-cancellation.json
```

Use a new report filename on each run. The probe verifies installed upstream
source and model hashes, restores the saved plan and semantic tokens, and checks
pre-cancelled planning, planning/semantic cancellation after eight tokens, and
acoustic cancellation at the third callback check. It writes no new audio.
Reported exception latency is relative to the synthetic flag, not an arbitrary
external UI cancellation. CUDA allocator values after `close()`/collection are
recorded without claiming zero driver overhead or a proven leak. Model-load,
decoder, external process termination and cleanup deadlines require separate tests.

## Portable engine test bundle

`bundle/make-bundle.ps1` assembles `.phase0/test-bundle/` from the
multi-architecture build: `yue-synth` and the ggml DLLs with app-local Visual
C++ and OpenMP runtime DLLs, the verified cuBLAS pack in `runtime/cublas`, the
converted short/full requests, and `run-test.ps1`. It also writes
`.phase0/alunan-engine-test.wsb` for Windows Sandbox (networking and vGPU off,
bundle and models mapped read-only, `.phase0/sandbox-results` writable).

`run-test.ps1 -Bundle <dir> -Models <dir> -Results <dir> [-Fixture full]` records
the OS, whether the C++ runtime exists in System32, a negative control run of
the engine without its app-local runtime DLLs, a load check, one generation, and
every DLL the process maps. It also records the power source (with a warning on
battery), GPU memory, clocks, power and throttle reasons from `nvidia-smi`, and
the process's dedicated versus shared GPU memory from Windows counters (shared
usage means VRAM overflowed). In the sandbox there is no CUDA device, so the
engine falls back to the CPU. On another NVIDIA PC, copy the bundle and the two
GGUFs and run the script there.

## Other platforms

[`MACOS-RUNBOOK.md`](MACOS-RUNBOOK.md) is the step-by-step procedure for the
Apple Silicon Mac evaluation. [`LINUX-RUNBOOK.md`](LINUX-RUNBOOK.md) covers native
Ubuntu 24.04 with NVIDIA CUDA (and a Linux RTX 5090 cloud container). `prepare-models.py` is a cross-platform
equivalent of `prepare-models.ps1`, and `run-cpp.py` runs on macOS and Linux as
well as Windows (engine name, library hashing, and memory sampling adapt).

## Portable and cloud test kits

`bundle/make-portable-kit.ps1` builds `.phase0/rtx30-kit/` (about 4.6 GB): the
engine bundle, the two pinned GGUFs, and `RUN-TEST.cmd`, which verifies the
models, runs the short and full songs, and leaves a `results` folder to send
back. Copy the folder to another Windows PC with an NVIDIA driver and
double-click `RUN-TEST.cmd`.

`cloud/run-cloud-kit.sh` is the Linux cloud GPU equivalent (for example an RTX
5090 pod); see [`cloud/README.md`](cloud/README.md). It builds on the pod and
downloads its own verified inputs.

`prepare-runtime-pack.py --pack <id>` downloads, verifies and allow-list
extracts a vendor GPU runtime pack pinned in
[`runtime-packs.lock.json`](../../docs/validation/phase0/runtime-packs.lock.json),
writing `.phase0/runtime-packs/<id>/files/` and `files.json`.
`probe-cpp-termination.py` accepts `--build`, `--request-json` and
`--complete-take` so it runs against Linux builds too.
