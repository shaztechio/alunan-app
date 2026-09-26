# Phase 0 cloud GPU kit (RTX 50-series)

[`run-cloud-kit.sh`](run-cloud-kit.sh) runs the Phase 0 engine tests on a rented
Linux GPU, primarily an RTX 5090 for Blackwell (`sm_120a`) evidence. Everything
runs inside the pod; nothing is copied from your PC. It is a developer research
procedure, not the app.

## What it does

1. Checks the GPU, the driver (580 or newer for CUDA 13), and free disk space.
2. Installs build packages in the container and confirms CUDA 13.3 `nvcc`.
3. Clones this repository and the pinned yue2.cpp source, and builds `yue-synth`
   for the same GPU list as Windows (`75;86;89;120a` plus PTX).
4. Downloads and verifies the pinned Q8 models (4.34 GB) and NVIDIA's pinned
   Linux cuBLAS archive (818 MB), extracting only the two libraries.
5. Runs the short song in two processes, the full song, three more full songs,
   and a short song with only the downloaded cuBLAS on the library path.
6. Kills the engine at five stages and during the final write.
7. Packs everything into `/workspace/alunan-results-<time>.tar.gz` (about 300 MB
   with the audio).

Expect 30–60 minutes, mostly the build. At $0.30–$1 per hour that is about
$1 or less, plus storage while the pod exists.

## Deploy (RunPod example; other providers are similar)

1. Create a GPU pod with **1× RTX 5090**.
2. Use a custom container image: `nvidia/cuda:13.3.1-devel-ubuntu24.04`.
3. Set container or volume disk to **at least 40 GB**, mounted at `/workspace`.
4. Start the pod and open its web terminal (or SSH).
5. Run:

   ```bash
   apt-get update -qq && apt-get install -y -qq curl
   curl -fsSL https://raw.githubusercontent.com/shaztechio/alunan-app/main/tools/phase0/cloud/run-cloud-kit.sh -o run-cloud-kit.sh
   bash run-cloud-kit.sh
   ```

On Vast.ai, choose the same image, 40 GB of disk, and an instance whose listed
driver is 580 or newer; if `/workspace` does not exist, run with
`WORK=/root bash run-cloud-kit.sh`. To test a branch that is not merged yet,
set `ALUNAN_REF=<branch>`.

If the script stops at the driver check, the host's driver is too old for CUDA
13: delete the pod and choose another host.

## Get the results, then stop billing

Download the `.tar.gz` with the provider's file browser, `scp` over SSH, or
RunPod's `runpodctl send`. Put it anywhere on your PC and tell Claude where it
is; the Phase 0 records are written from it in a PR.

Then **stop and delete the pod** (and any attached volume). A stopped pod can
still bill for storage.

## What this does and does not prove

It proves the engine builds on Linux with CUDA 13.3, that the RTX 50-series
code runs, the Linux runtime-pack loading, and termination behavior on that GPU.
It is a cloud container, not a native Ubuntu desktop: GTK, packaging, and
desktop behavior still need the native Linux runbook
([`LINUX-RUNBOOK.md`](../LINUX-RUNBOOK.md)).
