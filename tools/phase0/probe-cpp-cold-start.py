"""Developer-only probe: yue-synth startup with model files outside the OS cache.

Clearing the Windows standby list needs administrator tools, so this copies the
pinned GGUFs with unbuffered I/O (robocopy /J), which leaves the copies out of
the file cache, then runs the short fixture twice on those copies: a cold run
and an immediately repeated warm run. It records per-stage load times from the
engine log, whole-process time, process read/write byte counters (an upper
bound on temporary disk writes), and new files under TEMP. The copies are
hashed only after the cold run, so hashing cannot warm them first, and are
deleted at the end. Run with the reference venv.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / ".phase0/yue2-cpp-build-cuda-sm89"
REQUEST = ROOT / ".phase0/runs/windows-short-cpp-q8/request.json"
LOAD = re.compile(r"\[Store\] Load (LM|NAR|VAE): (\d+) ms")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def temp_files():
    root = Path(tempfile.gettempdir())
    found = {}
    for path in root.rglob("*"):
        try:
            if path.is_file():
                found[str(path)] = path.stat().st_size
        except OSError:
            pass
    return found


def run(label, model, vae, work):
    import psutil
    take = work / label
    take.mkdir()
    command = [str(BUILD / "yue-synth.exe"), "--model", str(model), "--vae", str(vae),
               "--request", str(REQUEST), "--out", str(take / "audio.wav")]
    before_temp = temp_files()
    started = time.perf_counter()
    with (take / "stderr.log").open("w", encoding="utf-8") as log:
        child = subprocess.Popen(command, stdout=log, stderr=log, cwd=take)
        proc = psutil.Process(child.pid)
        io = {}
        stop = threading.Event()

        def sample():
            while not stop.wait(0.05):
                try:
                    counters = proc.io_counters()
                    io.update(read=counters.read_bytes, write=counters.write_bytes)
                except psutil.Error:
                    pass

        monitor = threading.Thread(target=sample, daemon=True)
        monitor.start()
        code = child.wait()
        seconds = time.perf_counter() - started
        stop.set()
        monitor.join(timeout=2)
    after_temp = temp_files()
    text = (take / "stderr.log").read_text(encoding="utf-8", errors="replace")
    new_temp = {k: v for k, v in after_temp.items() if k not in before_temp}
    return {"label": label, "exitCode": code, "processSeconds": seconds,
            "loadMs": {m[0]: int(m[1]) for m in LOAD.findall(text)},
            "processReadBytesAtLastSample": io.get("read"), "processWriteBytesAtLastSample": io.get("write"),
            "outputBytes": sum(p.stat().st_size for p in take.iterdir() if p.is_file() and p.name != "stderr.log"),
            "newTempFiles": len(new_temp), "newTempBytes": sum(new_temp.values()),
            "wavSha256": digest(take / "audio.wav") if (take / "audio.wav").exists() else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    if args.report.exists():
        raise SystemExit("Refusing to overwrite an existing report")
    work = ROOT / ".phase0/runs" / args.report.stem
    work.mkdir(parents=True, exist_ok=False)
    copies = ROOT / ".phase0/cold-copies"
    copies.mkdir(exist_ok=False)
    lock = json.loads((ROOT / "docs/validation/phase0/model-profiles.lock.json").read_text(encoding="utf-8-sig"))
    profile = next(p for p in lock["profiles"] if p["id"] == "yue2-cpp-q8")
    wanted = {a["path"]: a for a in profile["assets"] if a["path"].endswith(".gguf")}
    source = ROOT / ".phase0/models/Serveurperso/YuE2-GGUF" / next(iter(wanted.values()))["revision"]
    report = {"schemaVersion": 1, "platform": platform.platform(), "binary": digest(BUILD / "yue-synth.exe"),
              "method": "robocopy /J (unbuffered) copies of the pinned GGUFs; cold run on the copies, then a warm repeat",
              "ioScope": "psutil io_counters sampled every 50 ms until exit; includes model reads and output writes"}
    try:
        copied = time.perf_counter()
        result = subprocess.run(["robocopy", str(source), str(copies), *wanted, "/J", "/NP", "/NJH", "/NJS"],
                                capture_output=True, text=True)
        if result.returncode >= 8:
            raise SystemExit(f"robocopy failed: {result.returncode}\n{result.stdout}")
        report["copySeconds"] = time.perf_counter() - copied
        for name, asset in wanted.items():
            if (copies / name).stat().st_size != asset["bytes"]:
                raise SystemExit(f"Copy size mismatch: {name}")
        model, vae = copies / "YuE2-3B-Q8_0.gguf", copies / "YuE2-Vae-F32.gguf"
        time.sleep(2)
        report["cold"] = run("cold", model, vae, work)
        report["warm"] = run("warm", model, vae, work)
        report["copiesMatchPins"] = all(digest(copies / n) == a["sha256"] for n, a in wanted.items())
    finally:
        shutil.rmtree(copies, ignore_errors=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("copySeconds", "cold", "warm", "copiesMatchPins")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
