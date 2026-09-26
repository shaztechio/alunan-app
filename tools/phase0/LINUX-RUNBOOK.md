# Phase 0 runbook: native Linux (NVIDIA CUDA)

Primary target: this development PC (RTX 4090) booted into Ubuntu 24.04 LTS
installed on an external USB SSD, so results compare directly with the Windows
records on the same GPU. The same steps, minus GTK (step 10) and cold cache
(step 8), also serve a rented Linux RTX 5090 container for Blackwell (`sm_120a`)
evidence; record that as a cloud container, not a native desktop.

This produces the Linux evidence for P0-01, P0-02, P0-03, P0-04 and P0-07. It
is a developer research procedure, not user setup or Phase 1 work. Follow
[`AGENTS.md`](../../AGENTS.md): changes land through a PR with Conventional
Commit messages, research files stay in ignored `.phase0/`, and a failed or
skipped step is recorded as Failed or Not run. WSL results do not count here.

Read first: [`spec/FEATURES.md`](../../spec/FEATURES.md) (APP-002, MOD-015,
GEN-010), [the decision record](../../docs/decisions/0001-engine-feasibility.md),
[the evidence ledger](../../docs/validation/phase0/README.md), and
[`tools/phase0/README.md`](README.md). The Windows records are the baseline.

## 1. Record the machine

```bash
lsb_release -a; uname -r
nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv
lscpu | head -20; free -b
lsblk -o NAME,SIZE,TRAN,MODEL,MOUNTPOINTS
```

The driver must be 580 or newer for CUDA 13. Note that the repository and models
live on the USB SSD (`TRAN=usb`): load times are not comparable with the
Windows NVMe runs, and the record must say so.

## 2. Developer tools (build machine only)

```bash
sudo apt update && sudo apt install -y build-essential git curl python3-venv
```

Install the CUDA 13.3 toolkit from NVIDIA's Ubuntu 24.04 repository (see
NVIDIA's CUDA downloads page), package `cuda-toolkit-13-3`, and confirm
`nvcc --version` reports 13.3.73 as on Windows. The toolkit is a build
requirement only; step 7 proves the engine runs without it.

```bash
python3 -m venv .phase0/linux-venv
.phase0/linux-venv/bin/pip install numpy==2.2.6 psutil==7.2.2 soundfile==0.13.1 cmake ninja
.phase0/linux-venv/bin/pip freeze > .phase0/linux-venv-freeze.txt
.phase0/linux-venv/bin/python tools/phase0/validate-locks.py
```

Ubuntu 24.04 ships Python 3.12, which the tools need (`hashlib.file_digest`).

## 3. Pinned engine source

```bash
git clone --no-checkout https://github.com/ServeurpersoCom/yue2.cpp.git .phase0/yue2-cpp-git
git -C .phase0/yue2-cpp-git checkout --detach f17d5268483db25c9d79a9d53967f9d31fd1ccd3
git -C .phase0/yue2-cpp-git submodule update --init --recursive
git -C .phase0/yue2-cpp-git submodule status   # expect 765bc96f9bb8d4c397c91c23b4e5c52a93fcf9b0
```

## 4. Build

Use the same architecture list as the Windows multi-architecture build.

```bash
export PATH=/usr/local/cuda-13.3/bin:$PWD/.phase0/linux-venv/bin:$PATH
cmake -S .phase0/yue2-cpp-git -B .phase0/yue2-cpp-build-cuda-multi -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON -DGGML_NATIVE=OFF "-DCMAKE_CUDA_ARCHITECTURES=75-real;86-real;89-real;120-real;120-virtual"
cmake --build .phase0/yue2-cpp-build-cuda-multi --target yue-synth
B=.phase0/yue2-cpp-build-cuda-multi
$B/yue-synth --help | head -1          # expect "yue2.cpp f17d526 (2026-09-24)"
sha256sum $B/yue-synth $B/*.so*
ldd $B/yue-synth $B/libggml-cuda.so
readelf -d $B/yue-synth | grep -E 'RPATH|RUNPATH'
objdump -T $B/*.so* $B/yue-synth | grep -o 'GLIBC_[0-9.]*' | sort -uV | tail -1
```

Record gcc and nvcc versions, flags, hashes, `ldd` output, RUNPATH, and the
highest required glibc version (the Linux compatibility floor). Expect
`libcublas.so.13`, `libcublasLt.so.13`, `libgomp.so.1`, `libstdc++.so.6`,
`libgcc_s.so.1` and glibc. Anything not in a base Ubuntu 24.04 install (at least
cuBLAS and, in a minimal image, `libgomp`) must be bundled or supplied by the
runtime pack; list each one.

## 5. Linux cuBLAS runtime pack

Pinned from NVIDIA's `redistrib_13.3.1.json` (cuBLAS 13.6.0.2, the same version
as Windows):

| Field | Value |
| --- | --- |
| URL | `https://developer.download.nvidia.com/compute/cuda/redist/libcublas/linux-x86_64/libcublas-linux-x86_64-13.6.0.2-archive.tar.xz` |
| Bytes | 817,981,368 |
| SHA-256 | `1794edb653adf48f5fa02d86bb738ed75888dd355aa39dadb6202d84d554c0dc` |

```bash
P=.phase0/runtime-packs/cublas-13.6.0.2-linux-x64 && mkdir -p $P && cd $P
curl -fL --continue-at - -o archive.tar.xz.incomplete \
  https://developer.download.nvidia.com/compute/cuda/redist/libcublas/linux-x86_64/libcublas-linux-x86_64-13.6.0.2-archive.tar.xz
stat -c %s archive.tar.xz.incomplete && sha256sum archive.tar.xz.incomplete   # compare with the table
mv archive.tar.xz.incomplete libcublas-linux-x86_64-13.6.0.2-archive.tar.xz
tar -tvJf libcublas-linux-x86_64-13.6.0.2-archive.tar.xz > entries.txt
cd -
```

Inspect `entries.txt` for absolute paths, `..`, and links. The archive is
expected to contain `libcublas.so.13 -> libcublas.so.13.x.y` style symlinks.
MOD-015 and DATA-FORMATS reject links during extraction, so extract only the
two real library files by exact name and save them under their sonames
(`libcublas.so.13`, `libcublasLt.so.13`) in `$P/files/`, plus the `LICENSE`.
Record each file's size and SHA-256, compare with the toolkit copies under
`/usr/local/cuda-13.3`, and note the compressed/extracted sizes (the Linux
archive is larger than the Windows one because it also carries static
libraries the app never downloads separately; that cost is a finding).

## 6. Models

```bash
.phase0/linux-venv/bin/python tools/phase0/prepare-models.py --profile yue2-cpp-q8
```

## 7. Generation runs

```bash
B=.phase0/yue2-cpp-build-cuda-multi; PY=.phase0/linux-venv/bin/python
$PY tools/phase0/run-cpp.py --build $B --request tools/phase0/requests/short.json --output .phase0/runs/linux-short-cpp-q8 --repeat 2
$PY tools/phase0/run-cpp.py --build $B --request tools/phase0/requests/full.json --output .phase0/runs/linux-full-cpp-q8
$PY tools/phase0/run-cpp.py --build $B --request tools/phase0/requests/full.json --output .phase0/runs/linux-full-cpp-q8-repeat5 --repeat 5
```

Pass criteria match Windows: CUDA backend lines in each `stderr.log`, exit 0,
finite non-silent 48 kHz stereo WAV, no `(truncated)` stage. Compare stage
timings, peak RSS, GPU peak, and WAV hashes with `windows-short-cpp-q8.json`
and `windows-full-cpp-q8.json`; identical hashes are not required across
operating systems, but note whether they match.

Toolkit-free run with the runtime pack:

```bash
$PY tools/phase0/run-cpp.py --build $B --request tools/phase0/requests/short.json \
  --output .phase0/runs/linux-short-cpp-q8-runtime-pack --runtime-dir .phase0/runtime-packs/cublas-13.6.0.2-linux-x64/files
```

On Linux `--runtime-dir` sets `LD_LIBRARY_PATH` to the pack only and removes
`CUDA_HOME`/`CUDA_PATH*`, then records mapped libraries in `loadedDlls` and
toolkit paths in `toolkitDllsLoaded` (names kept from Windows). The toolkit's
`ld.so.conf.d` entry means the ldconfig cache can still offer its cuBLAS, so
confirm from `loadedDlls` that `libcublas*.so.13` came from the pack. If the
toolkit copy wins, record it, then retest with the toolkit's ldconfig entry
disabled or the toolkit removed. For Phase 3, record which mechanism would make
the worker load cuBLAS by full path (for example an `$ORIGIN`-relative RUNPATH
to the runtime cache, or `dlopen` of the absolute path before loading ggml).

## 8. Failure and lifecycle probes

The Windows probes need small ports; keep their method and report format:

- `probe-cpp-termination.py`: set `BUILD` to the Linux build and the engine name
  without `.exe` (`nvidia-smi` works on Linux). Run the five stage kills and
  the `--final-write` sweep. On Linux, check whether a kill during the final
  write also leaves a truncated but parseable WAV.
- `probe-cpp-failures.py`: same Linux adjustments. Run the bad-file cases and
  the VRAM holder case. Linux has no WDDM paging, so scarce VRAM may produce a
  real CUDA out-of-memory error here: record the message, exit code, and GPU
  release.
- `probe-cpp-cold-start.py`: replace the unbuffered `robocopy` copy with
  `sync; echo 3 | sudo tee /proc/sys/vm/drop_caches` before the cold run (needs
  the owner's approval for `sudo`). Note that the models sit on USB storage.
- CPU fallback: one short run with `GGML_BACKEND=CPU` for comparison with the
  Windows CPU record.

## 9. Clean-system library check

The Linux counterpart of the Windows Sandbox test: run the engine from a bundle
directory (engine, ggml libraries, `libgomp.so.1` if needed, and the cuBLAS
pack) inside a plain `ubuntu:24.04` container with no NVIDIA runtime, using
Podman or Docker. Without a GPU the engine should fall back to the CPU; the
goal is to prove no library is missing from a minimal system. Record `ldd`
inside the container and whether generation starts. If the NVIDIA Container
Toolkit is available, repeat with the GPU for a clean CUDA run.

## 10. GTK 4 and .NET baseline (P0-07)

Record the installed GTK version (`pkg-config --modversion gtk4` after
installing `libgtk-4-dev`, expected 4.14 on 24.04). Install the .NET 10 SDK and
build a throwaway Gir.Core 0.8.1 window in `.phase0/gtk-probe/` (not production
code) that opens, shows a label and a button, and closes. Publish it
self-contained and record which GTK, GLib, Pango, Cairo and graphics libraries
it maps (`ldd` on `libgtk-4.so.1` and `/proc/<pid>/maps` while running). This
sizes the private GTK closure the app must carry; it does not start the Linux
app.

## 11. Listening

Rate the Linux short and full takes with the scoring sheet criteria; for a
blind A/B against the Windows C++ takes, adapt `make-listening-kit.py` pairs.
The reviewer answers before the key is opened.

## 12. Evidence and decision

Add compact records under `docs/validation/phase0/` (`linux-build.json`,
`linux-runtime-pack.json`, `linux-short-cpp-q8.json`, `linux-full-cpp-q8.json`,
`linux-termination.json`, `linux-failures.json`, `linux-gtk-probe.json`) with
repository-relative paths and no user directories. Update the hardware table,
evidence ledger, P0 task table, decision record, and the plan's progress note.
Open a PR titled like `feat(phase0): evaluate yue2.cpp CUDA on native Ubuntu 24.04`.

Decision rule: if the Linux build passes the technical checks, the runtime pack
loads without the toolkit, and the clean-system check finds no missing library,
record CUDA yue2.cpp as the provisional Linux backend. Record the glibc floor
and the GTK closure as inputs to the Linux package-format decision (Phase 1).
