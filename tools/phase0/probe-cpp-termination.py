"""Developer-only probe: forced termination of yue-synth at each pipeline stage.

yue-synth has no cancellation channel, so Lagu's worker must be able to stop it
by terminating the process. For each stage this launches the pinned binary on
the short fixture, waits for a stderr marker, calls TerminateProcess (via
Popen.kill), and records: request-to-exit latency, time until device-wide GPU
memory returns near its pre-run baseline, whether any compute process remains,
and which output files were left behind. Run with the reference venv.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / ".phase0/yue2-cpp-build-cuda-sm89"
STAGES = [
    ("model-load", "[Load] LM backend"),
    ("score", "[AR] Score 100/"),
    ("semantic", "[AR] Semantic 100/"),
    ("acoustic", "[NAR] Step 5/"),
    ("decode", "[VAE] Graph:"),
]
TOLERANCE = 64 * 1024 * 1024


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def gpu_used():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits", "-i", "0"],
                         capture_output=True, text=True, check=True).stdout
    return int(out.strip()) * 1024 * 1024


def compute_pids():
    out = subprocess.run(["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
                         capture_output=True, text=True, check=True).stdout
    return {int(x) for x in out.split() if x.strip().isdigit()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    if args.report.exists():
        raise SystemExit("Refusing to overwrite an existing report")
    work = ROOT / ".phase0/runs" / args.report.stem
    work.mkdir(parents=True, exist_ok=False)
    lock = json.loads((ROOT / "docs/validation/phase0/model-profiles.lock.json").read_text(encoding="utf-8-sig"))
    profile = next(p for p in lock["profiles"] if p["id"] == "yue2-cpp-q8")
    assets = {}
    for asset in profile["assets"]:
        path = ROOT / ".phase0/models" / asset["repository"] / asset["revision"] / asset["path"]
        if path.stat().st_size != asset["bytes"] or digest(path) != asset["sha256"]:
            raise SystemExit(f"Asset integrity failure: {asset['path']}")
        assets[asset["path"]] = path
    source = ROOT / ".phase0/runs/windows-short-cpp-q8/request.json"
    report = {"schemaVersion": 1, "platform": platform.platform(), "binary": digest(BUILD / "yue-synth.exe"),
              "requestSha256": digest(source), "method": "Popen.kill (TerminateProcess) on first stderr marker",
              "gpuScope": "device-wide nvidia-smi memory.used; released = within 64 MiB of the pre-run baseline",
              "probes": []}
    for stage, marker in STAGES:
        take = work / stage
        take.mkdir()
        command = [str(BUILD / "yue-synth.exe"), "--model", str(assets["YuE2-3B-Q8_0.gguf"]),
                   "--vae", str(assets["YuE2-Vae-F32.gguf"]), "--request", str(source),
                   "--out", str(take / "audio.wav"), "--score", str(take / "score.abc"),
                   "--tokens", str(take / "tokens.csv"), "--latent", str(take / "latent.vae")]
        time.sleep(3)
        baseline = gpu_used()
        started = time.perf_counter()
        child = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, cwd=take,
                                 text=True, encoding="utf-8", errors="replace", bufsize=1)
        probe = {"stage": stage, "marker": marker, "gpuBaselineBytes": baseline}
        log = []
        for line in child.stderr:
            log.append(line)
            if marker in line:
                probe["markerSeconds"] = time.perf_counter() - started
                probe["gpuAtKillAboveBaselineBytes"] = gpu_used() - baseline
                requested = time.perf_counter()
                child.kill()
                child.wait()
                probe["exitSeconds"] = time.perf_counter() - requested
                probe["exitCode"] = child.returncode
                released = None
                while time.perf_counter() - requested < 30:
                    if gpu_used() - baseline <= TOLERANCE:
                        released = time.perf_counter() - requested
                        break
                    time.sleep(0.05)
                probe["gpuReleasedSeconds"] = released
                probe["processStillOnGpu"] = child.pid in compute_pids()
                break
        else:
            child.wait()
            probe["error"] = f"marker not seen; exit code {child.returncode}"
        (take / "stderr.log").write_text("".join(log), encoding="utf-8")
        probe["filesLeft"] = {p.name: p.stat().st_size for p in take.iterdir() if p.name != "stderr.log"}
        report["probes"].append(probe)
        print(json.dumps(probe), flush=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if all("error" not in p for p in report["probes"]) else 1


if __name__ == "__main__":
    sys.exit(main())
