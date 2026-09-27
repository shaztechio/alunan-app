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
$1 or less, plus storage while the instance exists.

## Start the kit (any provider)

Once you have a shell on the instance, start the kit in the background so a
dropped connection does not stop it, then follow its log (Ctrl+C stops the
following, not the run):

```bash
apt-get update -qq && apt-get install -y -qq curl
curl -fsSL https://raw.githubusercontent.com/shaztechio/alunan-app/main/tools/phase0/cloud/run-cloud-kit.sh -o run-cloud-kit.sh
nohup bash run-cloud-kit.sh > kit.out 2>&1 &
tail -f kit.out
```

The run is finished when `kit.out` ends with `Done` and names the
`/workspace/alunan-results-<time>.tar.gz` file. For scripted watching, read
`/workspace/alunan-kit.status`: `running`, `done`, or `failed <exit code>`
(`alunan-kit.result` then holds the archive path). Do not detect completion
with `pgrep -f run-cloud-kit.sh` from an SSH command: the command's own text
matches the pattern, so the check never reports the kit as stopped. The script creates `/workspace`
if the image lacks it; set `WORK=<dir>` to use another folder. To test a branch
that is not merged yet, set `ALUNAN_REF=<branch>`. If the script stops at the
driver check, the host's driver is too old for CUDA 13: remove the instance and
choose another host.

## RunPod

1. Create a GPU pod with **1× RTX 5090**.
2. Use a custom container image: `nvidia/cuda:13.3.1-devel-ubuntu24.04`.
3. Set container or volume disk to **at least 40 GB**, mounted at `/workspace`.
4. Start the pod, open its web terminal (or SSH), and start the kit as above.
5. Download the results with the pod's file browser, `scp`, or `runpodctl send`.
6. **Stop and delete the pod** and any attached volume; a stopped pod can still
   bill for storage.

## Vast.ai

1. Add your SSH public key to your Vast account (Account, SSH keys). SSH is the
   most dependable way into a custom image; Jupyter or web-terminal modes may
   not work with a bare CUDA image.
2. Search for **1× RTX 5090** and filter or sort by the host's listed
   **Max CUDA: choose 13.3 or higher**. The `nvidia/cuda:13.3.1` image can refuse
   to start on a host whose driver supports an older CUDA, before the script's
   own driver check can run.
3. Choose **on-demand**, not interruptible (bid) pricing, so the 30–60 minute
   run is not stopped midway. Prefer verified hosts with high reliability.
4. In the template, set the image to `nvidia/cuda:13.3.1-devel-ubuntu24.04`,
   the launch mode to **SSH**, and the disk to **at least 40 GB**. Disk size is
   fixed when the instance is created.
5. Rent it, then connect with the SSH command from the instance's **Connect**
   button (it includes a non-standard port) and start the kit as above.
6. From a terminal on your PC, copy the results using that port and address:

   ```bash
   scp -P <port> root@<address>:/workspace/alunan-results-*.tar.gz .
   ```

7. **Destroy the instance.** A stopped Vast instance keeps billing for its disk
   until it is destroyed.

## Get the results to Claude

Put the `.tar.gz` anywhere on your PC and tell Claude where it is; the Phase 0
records are written from it in a PR.

## What this does and does not prove

It proves the engine builds on Linux with CUDA 13.3, that the RTX 50-series
code runs, the Linux runtime-pack loading, and termination behavior on that GPU.
It is a cloud container, not a native Ubuntu desktop: GTK, packaging, and
desktop behavior still need the native Linux runbook
([`LINUX-RUNBOOK.md`](../LINUX-RUNBOOK.md)).
