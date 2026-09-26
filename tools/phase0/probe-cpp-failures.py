"""Developer-only probe: how yue-synth fails on bad model files and scarce VRAM.

Asset cases use scratch copies under .phase0/failure-scratch (never the verified
cache): missing generator, missing decoder, truncated generator, corrupted
generator header, decoder passed as generator, and same-size corruption inside
the decoder's tensor data. The VRAM case holds most free GPU memory in a helper
process (torch) and runs the short fixture. Each case records exit code, time,
the engine's last error lines, output files, and whether GPU memory returned to
baseline. Scratch copies are deleted afterwards. Run with the reference venv.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / ".phase0/yue2-cpp-build-cuda-sm89"
REQUEST = ROOT / ".phase0/runs/windows-short-cpp-q8/request.json"
MODELS = ROOT / ".phase0/models/Serveurperso/YuE2-GGUF/64b030e3deb6e8150d2b7c0db641ef5a17eca8a3"
SCRATCH = ROOT / ".phase0/failure-scratch"
HOLDER = r"""
import sys, time, torch
free, total = torch.cuda.mem_get_info()
keep = int(sys.argv[1]) * 1024 * 1024
blocks = []
chunk = 256 * 1024 * 1024
while torch.cuda.mem_get_info()[0] - chunk > keep:
    blocks.append(torch.empty(chunk, dtype=torch.uint8, device="cuda"))
print(torch.cuda.mem_get_info()[0], flush=True)
sys.stdin.read()
"""


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def gpu_used():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits", "-i", "0"],
                         capture_output=True, text=True, check=True).stdout
    return int(out.strip()) * 1024 * 1024


def run_case(name, model, vae, work, timeout=300):
    take = work / name
    take.mkdir()
    command = [str(BUILD / "yue-synth.exe"), "--model", str(model), "--vae", str(vae),
               "--request", str(REQUEST), "--out", str(take / "audio.wav")]
    baseline = gpu_used()
    started = time.perf_counter()
    try:
        done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              cwd=take, timeout=timeout)
        code, err = done.returncode, done.stderr
    except subprocess.TimeoutExpired as expired:
        code, err = "timeout", expired.stderr or ""
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
    seconds = time.perf_counter() - started
    (take / "stderr.log").write_text(err, encoding="utf-8")
    time.sleep(1)
    lines = [l for l in err.splitlines() if l.strip()]
    result = {"case": name, "exitCode": code if isinstance(code, str) else (code & 0xFFFFFFFF),
              "seconds": seconds, "lastLines": lines[-4:],
              "errorLines": [l for l in lines if any(k in l for k in ("FATAL", "ERROR", "error", "failed", "out of memory"))][:6],
              "gpuAboveBaselineAfterBytes": gpu_used() - baseline,
              "outputs": {p.name: p.stat().st_size for p in take.iterdir() if p.name != "stderr.log"}}
    wav = take / "audio.wav"
    if wav.exists():
        import numpy as np
        import soundfile as sf
        audio, _ = sf.read(wav, always_2d=True)
        result["wav"] = {"finite": bool(np.isfinite(audio).all()), "peakAbs": float(np.nanmax(np.abs(audio))) if audio.size else 0.0,
                         "seconds": len(audio) / 48000}
    print(json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--keep-free-mib", type=int, nargs="+", default=[3072, 6144])
    args = parser.parse_args()
    if args.report.exists():
        raise SystemExit("Refusing to overwrite an existing report")
    work = ROOT / ".phase0/runs" / args.report.stem
    work.mkdir(parents=True, exist_ok=False)
    SCRATCH.mkdir(exist_ok=False)
    model, vae = MODELS / "YuE2-3B-Q8_0.gguf", MODELS / "YuE2-Vae-F32.gguf"
    report = {"schemaVersion": 1, "platform": platform.platform(), "binary": digest(BUILD / "yue-synth.exe"),
              "requestSha256": digest(REQUEST), "cases": []}
    try:
        truncated = SCRATCH / "truncated-Q8.gguf"
        with model.open("rb") as src, truncated.open("wb") as dst:
            dst.write(src.read(model.stat().st_size // 2))
        bad_header = SCRATCH / "bad-header-Q8.gguf"
        shutil.copyfile(model, bad_header)
        with bad_header.open("r+b") as f:
            f.write(b"XXXX")
        corrupt_vae = SCRATCH / "corrupt-data-Vae.gguf"
        shutil.copyfile(vae, corrupt_vae)
        size = corrupt_vae.stat().st_size
        with corrupt_vae.open("r+b") as f:
            for offset in range(size // 4, size - 4096, size // 64):
                f.seek(offset)
                f.write(b"\xff\xff\x7f\x7f" * 1024)
        report["scratch"] = {"truncatedBytes": truncated.stat().st_size, "corruptVaeSameSize": corrupt_vae.stat().st_size == size,
                             "corruptVaeSha256": digest(corrupt_vae)}
        cases = [("missing-generator", SCRATCH / "absent.gguf", vae),
                 ("missing-decoder", model, SCRATCH / "absent-vae.gguf"),
                 ("truncated-generator", truncated, vae),
                 ("bad-header-generator", bad_header, vae),
                 ("decoder-as-generator", vae, vae),
                 ("same-size-corrupt-decoder", model, corrupt_vae)]
        for name, m, v in cases:
            report["cases"].append(run_case(name, m, v, work))
        python = ROOT / ".phase0/reference-venv/Scripts/python.exe"
        for keep in args.keep_free_mib:
            holder = subprocess.Popen([str(python), "-c", HOLDER, str(keep)], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, text=True)
            free = int(holder.stdout.readline().strip())
            try:
                result = run_case(f"vram-free-{keep}MiB", model, vae, work)
                result["freeVramBytesAtStart"] = free
                report["cases"].append(result)
            finally:
                holder.stdin.close()
                holder.wait(timeout=30)
                time.sleep(2)
    finally:
        shutil.rmtree(SCRATCH, ignore_errors=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
