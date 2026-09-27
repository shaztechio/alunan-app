#!/usr/bin/env bash
# Phase 0 cloud GPU kit (developer research, not the app). Run inside a Linux GPU
# container based on nvidia/cuda:13.3.1-devel-ubuntu24.04. It builds the pinned
# yue2.cpp engine, downloads and verifies the pinned models and NVIDIA's Linux
# cuBLAS archive, runs the Phase 0 generation and termination tests, and packs
# the results into one .tar.gz to download. See tools/phase0/cloud/README.md.
set -euo pipefail

WORK=${WORK:-/workspace}
REF=${ALUNAN_REF:-main}
REPO_URL=https://github.com/shaztechio/alunan-app.git
ARCHS="75-real;86-real;89-real;120-real;120-virtual"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$WORK"
RESULTS="$WORK/alunan-results-$STAMP"
mkdir -p "$RESULTS"
exec > >(tee -a "$RESULTS/kit.log") 2>&1
step() { echo; echo "=== $(date -u +%H:%M:%S) $*"; }
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO=sudo

step "Preflight"
command -v nvidia-smi >/dev/null || { echo "No nvidia-smi: this container has no NVIDIA GPU access."; exit 1; }
nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv | tee "$RESULTS/gpu.csv"
DRIVER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
if [ "${DRIVER%%.*}" -lt 580 ]; then
  echo "Driver $DRIVER is older than 580; CUDA 13 needs 580+. Pick another host."; exit 1
fi
FREE_GB=$(df -BG --output=avail "$WORK" | tail -1 | tr -dc 0-9)
[ "$FREE_GB" -ge 25 ] || { echo "Only ${FREE_GB} GB free in $WORK; need at least 25 GB."; exit 1; }
{ cat /etc/os-release; uname -a; nproc; free -b; df -h "$WORK"; } > "$RESULTS/machine.txt"

step "System packages"
export DEBIAN_FRONTEND=noninteractive
$SUDO apt-get update -qq
$SUDO apt-get install -y -qq git curl build-essential python3 python3-venv binutils > /dev/null
export PATH=/usr/local/cuda/bin:$PATH
nvcc --version | tee "$RESULTS/nvcc.txt"
grep -q "13.3" "$RESULTS/nvcc.txt" || echo "WARNING: nvcc is not CUDA 13.3; results will not match the Windows toolchain"

step "Repository ($REF)"
cd "$WORK"
[ -d alunan-app ] || git clone -q "$REPO_URL" alunan-app
cd alunan-app
git fetch -q origin "$REF" && git checkout -q FETCH_HEAD
git rev-parse HEAD | tee "$RESULTS/alunan-commit.txt"

step "Research venv"
python3 -m venv .phase0/linux-venv
PY=$PWD/.phase0/linux-venv/bin/python
.phase0/linux-venv/bin/pip install -q numpy==2.2.6 psutil==7.2.2 soundfile==0.13.1 cmake ninja
.phase0/linux-venv/bin/pip freeze > "$RESULTS/pip-freeze.txt"
export PATH=$PWD/.phase0/linux-venv/bin:$PATH
$PY tools/phase0/validate-locks.py

step "Pinned engine source"
if [ ! -d .phase0/yue2-cpp-git ]; then
  git clone -q --no-checkout https://github.com/ServeurpersoCom/yue2.cpp.git .phase0/yue2-cpp-git
  git -C .phase0/yue2-cpp-git checkout -q --detach f17d5268483db25c9d79a9d53967f9d31fd1ccd3
  git -C .phase0/yue2-cpp-git submodule update -q --init --recursive
fi
{ git -C .phase0/yue2-cpp-git rev-parse HEAD; git -C .phase0/yue2-cpp-git submodule status; } | tee "$RESULTS/engine-source.txt"

step "Build ($ARCHS)"
B=$PWD/.phase0/yue2-cpp-build-cuda-multi
if [ ! -x "$B/yue-synth" ]; then
  start=$(date +%s)
  cmake -S .phase0/yue2-cpp-git -B "$B" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DGGML_CUDA=ON -DGGML_NATIVE=OFF "-DCMAKE_CUDA_ARCHITECTURES=$ARCHS" > "$RESULTS/cmake-configure.log"
  cmake --build "$B" --target yue-synth > "$RESULTS/cmake-build.log"
  echo "buildSeconds $(( $(date +%s) - start ))" | tee "$RESULTS/build-time.txt"
fi
{
  # yue-synth --help exits 1 after printing usage; do not let that stop the kit.
  ("$B/yue-synth" --help 2>&1 || true) | head -1
  gcc --version | head -1; cmake --version | head -1
  sha256sum "$B/yue-synth" "$B"/*.so*
  ldd "$B/yue-synth" "$B"/libggml*.so* || true
  readelf -d "$B/yue-synth" | grep -E 'RPATH|RUNPATH' || true
  echo "glibc floor: $( (objdump -T "$B/yue-synth" "$B"/*.so* || true) | grep -o 'GLIBC_[0-9.]*' | sort -uV | tail -1)"
} > "$RESULTS/build.txt" 2>&1
cat "$RESULTS/build.txt"

step "Models (4.34 GB, verified)"
$PY tools/phase0/prepare-models.py --profile yue2-cpp-q8

step "NVIDIA Linux cuBLAS runtime pack (818 MB, verified)"
$PY tools/phase0/prepare-runtime-pack.py --pack cublas-13.6.0.2-linux-x64 | tee "$RESULTS/runtime-pack.json"
PACK=$PWD/.phase0/runtime-packs/cublas-13.6.0.2-linux-x64/files

RUNS=.phase0/runs
step "Short song, two processes"
$PY tools/phase0/run-cpp.py --build "$B" --request tools/phase0/requests/short.json --output $RUNS/cloud-short --repeat 2
step "Full song"
$PY tools/phase0/run-cpp.py --build "$B" --request tools/phase0/requests/full.json --output $RUNS/cloud-full
step "Full song, three more processes"
$PY tools/phase0/run-cpp.py --build "$B" --request tools/phase0/requests/full.json --output $RUNS/cloud-full-repeat3 --repeat 3
step "Short song with only the downloaded cuBLAS on the library path"
$PY tools/phase0/run-cpp.py --build "$B" --request tools/phase0/requests/short.json --output $RUNS/cloud-short-runtime-pack --runtime-dir "$PACK"
step "Termination at five stages"
$PY tools/phase0/probe-cpp-termination.py --build "$B" --request-json $RUNS/cloud-short/request.json $RUNS/cloud-termination.json
step "Termination during the final write"
$PY tools/phase0/probe-cpp-termination.py --final-write --build "$B" --request-json $RUNS/cloud-short/request.json \
  --complete-take $RUNS/cloud-short/take-1 $RUNS/cloud-final-write.json

step "Packing results"
cp -r $RUNS/cloud-short $RUNS/cloud-full $RUNS/cloud-full-repeat3 $RUNS/cloud-short-runtime-pack "$RESULTS/"
cp $RUNS/cloud-termination.json $RUNS/cloud-final-write.json "$RESULTS/"
cp .phase0/runtime-packs/cublas-13.6.0.2-linux-x64/files.json "$RESULTS/runtime-pack-files.json"
tar -czf "$RESULTS.tar.gz" -C "$WORK" "$(basename "$RESULTS")"
ls -lh "$RESULTS.tar.gz"
echo
echo "Done. Download $RESULTS.tar.gz, then STOP and DELETE the pod so billing ends."
