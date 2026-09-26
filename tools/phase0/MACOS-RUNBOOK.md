# Phase 0 runbook: Apple Silicon Mac (Metal)

Target machine: MacBook Pro, Apple M3, 16 GB unified memory. This runbook
produces the macOS evidence for P0-01, P0-03, P0-04, P0-05 and P0-07. It is a
developer research procedure, not a user setup or Phase 1 work. Follow
[`AGENTS.md`](../../AGENTS.md): every change lands through a PR with
Conventional Commit messages, research files stay in ignored `.phase0/`, and a
failed or skipped step is recorded as Failed or Not run, never as passing.

Read first: [`spec/FEATURES.md`](../../spec/FEATURES.md),
[the engine decision record](../../docs/decisions/0001-engine-feasibility.md),
[the evidence ledger](../../docs/validation/phase0/README.md), and
[`tools/phase0/README.md`](README.md). The Windows results there are the
baseline to compare against.

## 1. Record the machine

```bash
sw_vers
uname -m
sysctl -n machdep.cpu.brand_string hw.memsize
xcodebuild -version || xcode-select -p
clang --version | head -1
```

Store the output in the macOS evidence record (step 9). Developer tools on this
Mac (Xcode or its Command Line Tools, Python, CMake) are build-machine
requirements only; users of the app never install them.

## 2. Research environment

Use Python 3.12 (python.org installer or `uv python install 3.12`); the tools
need `hashlib.file_digest`, which Python 3.9 lacks.

```bash
git clone git@github.com:shaztechio/alunan-app.git && cd alunan-app
python3.12 -m venv .phase0/mac-venv
.phase0/mac-venv/bin/pip install numpy==2.2.6 psutil==7.2.2 soundfile==0.13.1 cmake ninja
.phase0/mac-venv/bin/pip freeze > .phase0/mac-venv-freeze.txt
.phase0/mac-venv/bin/python tools/phase0/validate-locks.py
```

## 3. Pinned engine source

Use a detached checkout so the engine's version string comes from upstream, not
from this repository (see the decision record). Compare the commit and submodule
with [`source-pins.json`](../../docs/validation/phase0/source-pins.json).

```bash
git clone --no-checkout https://github.com/ServeurpersoCom/yue2.cpp.git .phase0/yue2-cpp-git
git -C .phase0/yue2-cpp-git checkout --detach f17d5268483db25c9d79a9d53967f9d31fd1ccd3
git -C .phase0/yue2-cpp-git submodule update --init --recursive
git -C .phase0/yue2-cpp-git rev-parse HEAD
git -C .phase0/yue2-cpp-git submodule status   # expect 765bc96f9bb8d4c397c91c23b4e5c52a93fcf9b0
```

## 4. Build with Metal

macOS enables Metal and Accelerate automatically; the flags below make the
choices explicit and target the macOS 14 baseline under evaluation.

```bash
PATH="$PWD/.phase0/mac-venv/bin:$PATH" cmake -S .phase0/yue2-cpp-git -B .phase0/yue2-cpp-build-metal -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON -DGGML_NATIVE=OFF \
  -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_DEPLOYMENT_TARGET=14.0
PATH="$PWD/.phase0/mac-venv/bin:$PATH" cmake --build .phase0/yue2-cpp-build-metal --target yue-synth
.phase0/yue2-cpp-build-metal/yue-synth --help | head -1   # expect "yue2.cpp f17d526 (2026-09-24)"
shasum -a 256 .phase0/yue2-cpp-build-metal/yue-synth .phase0/yue2-cpp-build-metal/*.dylib
otool -L .phase0/yue2-cpp-build-metal/yue-synth .phase0/yue2-cpp-build-metal/*.dylib
```

Record compiler, SDK, CMake and flags, binary hashes, and the `otool -L`
dependencies. Expected: only system frameworks (Metal, Foundation, Accelerate)
and the build's own ggml libraries. Any Homebrew or `/usr/local` path is a
packaging defect to record. Confirm the Metal shader library is embedded
(no `.metallib` or `.metal` file needed beside the binary at run time).

## 5. Models

```bash
.phase0/mac-venv/bin/python tools/phase0/prepare-models.py --profile yue2-cpp-q8
```

This downloads 4.34 GB from the pinned Hugging Face revision and verifies every
file's size and SHA-256.

## 6. Generation runs

`run-cpp.py` works on macOS: it runs `yue-synth` without `.exe`, hashes the
build's libraries, and samples process RSS and system-wide used memory (Metal
allocations are not all counted in RSS). Close other heavy apps first and note
what else was running.

```bash
B=.phase0/yue2-cpp-build-metal
.phase0/mac-venv/bin/python tools/phase0/run-cpp.py --build $B --request tools/phase0/requests/short.json --output .phase0/runs/macos-short-metal-q8 --repeat 2
.phase0/mac-venv/bin/python tools/phase0/run-cpp.py --build $B --request tools/phase0/requests/full.json --output .phase0/runs/macos-full-metal-q8
.phase0/mac-venv/bin/python tools/phase0/run-cpp.py --build $B --request tools/phase0/requests/full.json --output .phase0/runs/macos-full-metal-q8-repeat3 --repeat 3
```

Check each `take-*/stderr.log` for the backend lines: the LM, NAR and VAE
backends must be Metal (for example `MTL0`), not CPU. Pass criteria match
Windows: finite, non-silent 48 kHz stereo WAV, no `(truncated)` stage, exit 0.
Record per-stage times from the log, whole-process time, peak RSS, and peak
system memory above baseline. Watch for swapping (`vm_stat` before and after,
or `memory_pressure`); heavy swap on 16 GB is a finding even if the song
completes. Compare with the Windows records (`windows-short-cpp-q8.json`,
`windows-full-cpp-q8.json`); different backends are not expected to produce
identical audio.

## 7. Failure behavior

Port the Windows probes only as far as needed, keeping their method:

- `probe-cpp-termination.py`: pass the Metal build path and engine name instead
  of the Windows defaults, and replace `nvidia-smi` with system memory release
  (`psutil.virtual_memory().used` back near its pre-run value). Kill at the
  same five stage markers plus the final-write sweep.
- `probe-cpp-failures.py`: run the missing, truncated, bad-header, wrong-file,
  and same-size-corrupt decoder cases (scratch copies only). Skip the VRAM
  holder case; on unified memory, record behavior under memory pressure instead
  if it can be produced safely.
- Cold start: flushing the file cache needs `sudo purge`; run it only if the
  owner approves, otherwise record cold start as Not run.

## 8. Listening

Rate the short and full Metal takes with the scoring sheet criteria from
`make-listening-kit.py`. For a blind comparison against Windows, copy the
Windows C++ takes onto the Mac and adapt the kit's pair paths. The reviewer
records answers before the key is opened.

## 9. Evidence and decision

Add compact records under `docs/validation/phase0/` (for example
`macos-build.json`, `macos-short-metal-q8.json`, `macos-full-metal-q8.json`,
`macos-termination.json`, `macos-failures.json`), with repository-relative paths
and no user directories. Update the hardware table, evidence ledger, P0 task
table, decision record, and `IMPLEMENTATION-PLAN.md` progress note. Open a PR
titled like `feat(phase0): evaluate yue2.cpp Metal on Apple M3 16 GB`.

P0-05 decision rule: if Metal passes the technical checks, the listening review,
and fits 16 GB without heavy swapping, record it as the provisional macOS
backend. If it fails correctness, quality, or memory, record the failure and
evaluate MLX next, bundled at build time, as the decision record says. Do not
adopt YuE2Mac's Homebrew or first-run bootstrap flow, and do not select the
PyTorch MPS route without reproducing and resolving upstream issue 176.

Also record for P0-07: Xcode and Swift versions, the macOS SDK, and whether a
build targeting macOS 14 succeeds. App signing and notarization are Phase 7.
