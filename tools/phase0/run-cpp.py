"""Developer-only yue2.cpp CLI benchmark; not the Lagu worker protocol.

Runs the pinned yue-synth binary once per process against the pinned Q8
profile, converting a fixed Phase 0 request into the C++ schema. Never starts
yue-server. Run with the reference venv (psutil, numpy, soundfile).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUILD = ROOT / ".phase0/yue2-cpp-build-cuda-sm89"
BINARIES = ("yue-synth.exe", "ggml.dll", "ggml-base.dll", "ggml-cpu.dll", "ggml-cuda.dll")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def gpu_used_bytes():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits", "-i", "0"],
                         capture_output=True, text=True, check=True).stdout
    return int(out.strip()) * 1024 * 1024


def convert(request):
    # Recipe from tools/phase0/README.md: same text and seed, 32 ODE steps,
    # one song/variation, wav32, and the default 360 s semantic budget.
    return {
        "style": request["style"], "lyrics": request["lyrics"], "cot": request["cot"],
        "lm_seed": request["seed"], "seed": request["seed"], "steps": 32,
        "lm_batch_size": 1, "synth_batch_size": 1, "duration": 360.0, "output_format": "wav32",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--repeat", type=int, default=1, help="separate yue-synth processes")
    parser.add_argument("--runtime-dir", type=Path,
                        help="run with PATH reduced to this directory plus Windows system folders and "
                             "CUDA_PATH* removed; records the DLL paths the process maps")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    args.output, args.build = args.output.resolve(), args.build.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = {
        "schemaVersion": 1, "status": "running", "engine": "yue2-cpp",
        "platform": platform.platform(), "requestSha256": digest(args.request), "runs": [],
        "memoryScope": "yue-synth process RSS sampled every 100 ms; GPU is device-wide nvidia-smi memory.used sampled every 250 ms minus the pre-run baseline, including any other GPU clients",
        "networkScope": "Not intercepted. Binaries import no WinSock/WinHTTP DLLs; not an OS firewall test",
        "cacheState": "Not flushed; each run is a new process but files may be in the OS cache",
    }
    import numpy as np
    import psutil
    import soundfile as sf
    try:
        report["binaries"] = {name: digest(args.build / name) for name in BINARIES}
        version = subprocess.run([str(args.build / "yue-synth.exe"), "--help"], capture_output=True, text=True)
        report["engineVersion"] = (version.stdout + version.stderr).strip().splitlines()[0]
        lock = json.loads((ROOT / "docs/validation/phase0/model-profiles.lock.json").read_text(encoding="utf-8-sig"))
        profile = next(p for p in lock["profiles"] if p["id"] == "yue2-cpp-q8")
        report["profile"] = profile["id"]
        paths = {}
        for asset in profile["assets"]:
            path = ROOT / ".phase0/models" / asset["repository"] / asset["revision"] / asset["path"]
            if path.stat().st_size != asset["bytes"] or digest(path) != asset["sha256"]:
                raise ValueError(f"Asset integrity failure: {asset['path']}")
            paths[asset["path"]] = path
        report["assetVerificationSeconds"] = time.perf_counter() - started
        model, vae = paths["YuE2-3B-Q8_0.gguf"], paths["YuE2-Vae-F32.gguf"]
        effective = convert(json.loads(args.request.read_text(encoding="utf-8")))
        request_path = args.output / "request.json"
        request_path.write_text(json.dumps(effective, indent=2) + "\n", encoding="utf-8")
        report["effectiveRequest"] = effective
        environment = None
        if args.runtime_dir:
            system = Path(os.environ["SystemRoot"])
            search = [args.runtime_dir.resolve(), system / "System32", system, system / "System32/Wbem"]
            environment = {k: v for k, v in os.environ.items() if not k.upper().startswith("CUDA_PATH")}
            environment["PATH"] = os.pathsep.join(str(d) for d in search)
            report["environment"] = {"PATH": [str(d) for d in search], "removed": sorted(
                k for k in os.environ if k.upper().startswith("CUDA_PATH"))}
        save_json(args.output / "benchmark.json", report)

        for index in range(args.repeat):
            take = args.output / f"take-{index + 1}"
            take.mkdir()
            wav = take / "audio.wav"
            command = [str(args.build / "yue-synth.exe"), "--model", str(model), "--vae", str(vae),
                       "--request", str(request_path), "--out", str(wav), "--score", str(take / "score.abc"),
                       "--tokens", str(take / "tokens.csv"), "--latent", str(take / "latent.vae")]
            baseline = gpu_used_bytes()
            peaks = {"rss": 0, "gpu": baseline}
            modules = set()
            stop = threading.Event()
            before = time.perf_counter()
            with (take / "stderr.log").open("w", encoding="utf-8") as log:
                child = subprocess.Popen(command, stdout=log, stderr=log, cwd=take, env=environment)
                proc = psutil.Process(child.pid)

                def sample():
                    ticks = 0
                    while not stop.wait(0.1):
                        try:
                            peaks["rss"] = max(peaks["rss"], proc.memory_info().rss)
                        except psutil.Error:
                            pass
                        ticks += 1
                        if ticks % 3 == 0:
                            peaks["gpu"] = max(peaks["gpu"], gpu_used_bytes())
                        if args.runtime_dir and ticks % 10 == 0:
                            try:
                                modules.update(m.path for m in proc.memory_maps() if m.path.lower().endswith(".dll"))
                            except psutil.Error:
                                pass

                monitor = threading.Thread(target=sample, daemon=True)
                monitor.start()
                code = child.wait()
                seconds = time.perf_counter() - before
                stop.set()
                monitor.join(timeout=5)
            text = (take / "stderr.log").read_text(encoding="utf-8", errors="replace")
            run = {"index": index + 1, "exitCode": code, "processSeconds": seconds,
                   "peakRssBytes": peaks["rss"], "gpuBaselineBytes": baseline,
                   "peakGpuUsedAboveBaselineBytes": peaks["gpu"] - baseline,
                   "arStages": re.findall(r"\[AR\] [^\n]*", text),
                   "truncated": "(truncated)" in text, "listeningReview": "not performed"}
            if args.runtime_dir:
                run["loadedDlls"] = sorted(modules, key=str.lower)
                run["toolkitDllsLoaded"] = sorted(m for m in modules if "nvidia gpu computing toolkit" in m.lower())
            report["runs"].append(run)
            save_json(args.output / "benchmark.json", report)
            if code != 0:
                raise RuntimeError(f"yue-synth exited with {code}")
            audio, rate = sf.read(wav, always_2d=True)
            valid = bool(audio.size and np.isfinite(audio).all() and np.max(np.abs(audio)) > 1e-6)
            run.update({"audioSeconds": len(audio) / rate, "sampleRate": rate, "channels": audio.shape[1],
                        "finiteNonSilentAudio": valid, "peakAbs": float(np.max(np.abs(audio))),
                        "wavSha256": digest(wav),
                        "outputBytes": sum(p.stat().st_size for p in take.rglob("*") if p.is_file())})
            save_json(args.output / "benchmark.json", report)
            if not valid or rate != 48000 or audio.shape[1] != 2 or run["truncated"]:
                raise RuntimeError("Run did not produce a complete finite non-silent 48 kHz stereo song")
        report["status"] = "passed-technical-checks-listening-pending"
    except BaseException as error:
        report["status"] = "failed"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        traceback.print_exc()
    finally:
        report["totalSeconds"] = time.perf_counter() - started
        save_json(args.output / "benchmark.json", report)
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
