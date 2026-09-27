"""Developer-only probe: full-path GPU runtime loading (FEATURES.md MOD-015, AC-017 preview).

Uses the prototype build from build-yue2-cpp-runtime-proto.cmd (patched yue-synth,
cuBLAS delay-loaded). Each case copies the engine into a fresh "app" folder,
optionally plants fake cuBLAS DLLs (random bytes) in the app folder, the working
directory and a folder prepended to PATH, runs the short fixture, and records
which cuBLAS files the process mapped, the exit code, and the WAV hash.
Windows only. Run with the reference venv (psutil).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / ".phase0/yue2-cpp-build-runtime-proto"
PACK = ROOT / ".phase0/runtime-packs/cublas-13.6.0.2-win-x64/files"
REQUEST = ROOT / ".phase0/runs/windows-short-cpp-q8/request.json"
MODELS = ROOT / ".phase0/models/Serveurperso/YuE2-GGUF/64b030e3deb6e8150d2b7c0db641ef5a17eca8a3"
ENGINE_FILES = ["yue-synth.exe", "ggml.dll", "ggml-base.dll", "ggml-cpu.dll", "ggml-cuda.dll"]
FAKES = ["cublas64_13.dll", "cublasLt64_13.dll"]
CASES = [
    ("default-search", {"env": False, "plant": False}),
    ("full-path-toolkit-on-path", {"env": True, "plant": False}),
    ("full-path-with-planted-fakes", {"env": True, "plant": True}),
    ("default-search-with-planted-fakes", {"env": False, "plant": True}),
    ("full-path-missing-pack", {"env": True, "plant": False, "pack": "missing"}),
]


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def plant(folder):
    folder.mkdir(parents=True, exist_ok=True)
    for name in FAKES:
        (folder / name).write_bytes(os.urandom(4096))


def main():
    import psutil
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    if args.report.exists():
        raise SystemExit("Refusing to overwrite an existing report")
    work = ROOT / ".phase0/runs" / args.report.stem
    work.mkdir(parents=True, exist_ok=False)
    report = {"schemaVersion": 1, "platform": platform.platform(),
              "binaries": {n: digest(BUILD / n) for n in ENGINE_FILES},
              "pack": {n: digest(PACK / n) for n in FAKES}, "cases": []}
    for name, case in CASES:
        base = work / name
        app, cwd, pathdir = base / "app", base / "cwd", base / "on-path"
        app.mkdir(parents=True)
        cwd.mkdir()
        for f in ENGINE_FILES:
            shutil.copy2(BUILD / f, app / f)
        if case["plant"]:
            plant(app)
            plant(cwd)
            plant(pathdir)
        env = dict(os.environ)
        env["PATH"] = os.pathsep.join([str(pathdir)] + env["PATH"].split(os.pathsep))
        env.pop("ALUNAN_GPU_RUNTIME_DIR", None)
        if case["env"]:
            env["ALUNAN_GPU_RUNTIME_DIR"] = str(base / "no-such-pack") if case.get("pack") == "missing" else str(PACK)
        wav = base / "audio.wav"
        command = [str(app / "yue-synth.exe"), "--model", str(MODELS / "YuE2-3B-Q8_0.gguf"),
                   "--vae", str(MODELS / "YuE2-Vae-F32.gguf"), "--request", str(REQUEST), "--out", str(wav)]
        mapped = set()
        stop = threading.Event()
        started = time.perf_counter()
        with (base / "stderr.log").open("w", encoding="utf-8") as log:
            child = subprocess.Popen(command, stdout=log, stderr=log, cwd=cwd, env=env)
            proc = psutil.Process(child.pid)

            def sample():
                while not stop.wait(0.5):
                    try:
                        mapped.update(m.path for m in proc.memory_maps() if "cublas" in m.path.lower())
                    except psutil.Error:
                        pass

            thread = threading.Thread(target=sample, daemon=True)
            thread.start()
            code = child.wait()
            stop.set()
            thread.join(timeout=2)
        text = (base / "stderr.log").read_text(encoding="utf-8", errors="replace")
        result = {"case": name, **case, "exitCode": code & 0xFFFFFFFF, "seconds": round(time.perf_counter() - started, 2),
                  "cublasMapped": sorted(str(Path(m).relative_to(ROOT)) if str(m).lower().startswith(str(ROOT).lower()) else m
                                         for m in mapped),
                  "runtimeLines": [l for l in text.splitlines() if l.startswith("[Runtime]")],
                  "wavSha256": digest(wav) if wav.exists() else None}
        report["cases"].append(result)
        print(json.dumps(result), flush=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
