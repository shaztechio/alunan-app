"""Developer-only local YuE2 benchmark; not the Alunan worker protocol."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cuda", "mps", "cpu"), default="cuda")
    parser.add_argument("--backend", choices=("torch", "torch-eager"), default="torch")
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = {
        "schemaVersion": 1, "status": "running",
        "platform": platform.platform(), "python": platform.python_version(),
        "requestSha256": digest(args.request), "runs": [], "networkAttempts": [],
        "memoryScope": "RSS sampled every 100 ms for this Python process; CUDA allocator peaks exclude driver/other processes",
        "networkScope": "Python audit hook blocks socket connect/DNS; not an OS firewall or native-library traffic capture",
        "cacheState": "Not flushed; first process run is not proof of an OS cold-cache startup",
    }
    stop = threading.Event()
    monitor = None
    pipe = None
    try:
        lock = json.loads((ROOT / "docs/validation/phase0/model-profiles.lock.json").read_text(encoding="utf-8-sig"))
        profile = next(p for p in lock["profiles"] if p["id"] == "yue2-reference-bf16")
        report["profile"] = profile["id"]
        report["profileLockSha256"] = digest(ROOT / "docs/validation/phase0/model-profiles.lock.json")
        components = {}
        for asset in profile["assets"]:
            folder = ROOT / ".phase0/models" / asset["repository"] / asset["revision"]
            path = folder / asset["path"]
            if path.stat().st_size != asset["bytes"] or digest(path) != asset["sha256"]:
                raise ValueError(f"Asset integrity failure: {asset['repository']}/{asset['path']}")
            components[asset["role"]] = folder
        report["assetVerificationSeconds"] = time.perf_counter() - started
        report["modelCacheBytes"] = profile["totalBytes"]
        for key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
            os.environ[key] = "1"

        def audit(event, event_args):
            if event in {"socket.connect", "socket.getaddrinfo", "socket.gethostbyname"}:
                report["networkAttempts"].append(event)
                raise RuntimeError(f"Offline benchmark blocked {event}")

        sys.addaudithook(audit)
        imported = time.perf_counter()
        import numpy as np
        import psutil
        import soundfile as sf
        import torch
        from yue2 import YuE2Pipeline
        report["importSeconds"] = time.perf_counter() - imported
        report["packages"] = {name: importlib.metadata.version(name) for name in (
            "torch", "transformers", "huggingface-hub", "safetensors", "tiktoken",
            "numpy", "soundfile", "accelerate", "psutil", "yue2-infer")}
        report["torchCuda"] = torch.version.cuda
        if args.device == "cuda":
            report["gpu"] = torch.cuda.get_device_name(0)
            report["gpuMemoryBytes"] = torch.cuda.get_device_properties(0).total_memory

        process = psutil.Process()
        memory = {"peakRssBytes": process.memory_info().rss}

        def sample_memory():
            while not stop.wait(0.1):
                memory["peakRssBytes"] = max(memory["peakRssBytes"], process.memory_info().rss)

        monitor = threading.Thread(target=sample_memory, daemon=True)
        monitor.start()
        request = json.loads(args.request.read_text(encoding="utf-8"))
        init_start = time.perf_counter()
        pipe = YuE2Pipeline.from_pretrained(
            str(components["generator"]), vae=str(components["decoder"]),
            local_files_only=True, device=args.device, backend=args.backend,
            memory_budget_gib=24, quantization="none", progress=True)
        report["pipelineInitSeconds"] = time.perf_counter() - init_start
        save_json(args.output / "benchmark.json", report)
        for index in range(args.repeat):
            if args.device == "cuda":
                torch.cuda.synchronize()
                torch.cuda.reset_peak_memory_stats()
            memory["peakRssBytes"] = process.memory_info().rss
            before = time.perf_counter()
            song = pipe(**request)
            generation_seconds = time.perf_counter() - before
            destination = args.output / f"take-{index + 1}"
            song.save_artifacts(destination)
            wav_path = destination / "audio.wav"
            song.save(wav_path)
            audio, sample_rate = sf.read(wav_path, always_2d=True)
            valid = bool(audio.size and np.isfinite(audio).all() and np.max(np.abs(audio)) > 1e-6)
            run = {
                "index": index + 1, "generationSeconds": generation_seconds,
                "saveSeconds": time.perf_counter() - before - generation_seconds,
                "audioSeconds": len(audio) / sample_rate, "sampleRate": sample_rate,
                "channels": audio.shape[1], "finiteNonSilentAudio": valid,
                "truncated": song.truncated, "timing": song.timing,
                "peakRssBytes": memory["peakRssBytes"],
                "rssAfterSaveBytes": process.memory_info().rss,
                "wavSha256": digest(wav_path),
                "outputBytes": sum(p.stat().st_size for p in destination.rglob("*") if p.is_file()),
                "listeningReview": "not performed",
            }
            if args.device == "cuda":
                run["peakCudaAllocatedBytes"] = torch.cuda.max_memory_allocated()
                run["peakCudaReservedBytes"] = torch.cuda.max_memory_reserved()
            report["runs"].append(run)
            save_json(args.output / "benchmark.json", report)
            if not valid or sample_rate != 48000 or audio.shape[1] != 2 or any(song.truncated.values()):
                raise RuntimeError("Run did not produce a complete finite non-silent 48 kHz stereo song")
            del song, audio
        report["status"] = "passed-technical-checks-listening-pending"
    except BaseException as error:
        report["status"] = "failed"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        traceback.print_exc()
    finally:
        if pipe is not None:
            pipe.close()
        stop.set()
        if monitor is not None:
            monitor.join(timeout=2)
        report["totalSeconds"] = time.perf_counter() - started
        save_json(args.output / "benchmark.json", report)
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
