"""Build a blind A/B listening kit from retained Phase 0 takes.

Developer research tool. For each fixture, the reference and candidate WAVs are
rewritten through one writer (identical float32 samples, identical header layout)
as A/B in random order, with a uniform timestamp, so file metadata does not
reveal the engine. Durations still differ between engines. The key is written to
a separate file so the reviewer can listen before looking at it. Run with the
reference venv (numpy, soundfile).
"""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / ".phase0/runs"
PAIRS = {
    "short": {"reference": RUNS / "windows-short-eager/take-1/audio.wav",
              "candidate": RUNS / "windows-short-cpp-q8/take-1/audio.wav"},
    "full": {"reference": RUNS / "windows-full-eager/take-1/audio.wav",
             "candidate": RUNS / "windows-full-cpp-q8/take-1/audio.wav"},
}
ENGINES = {"reference": "YuE2 Python torch-eager BF16", "candidate": "yue2.cpp Q8_0 + F32 VAE (CUDA)"}
CRITERIA = ["Lyric intelligibility", "Lyric completion and order", "Consistent voice",
            "Clipping, distortion or noise", "Coherent structure and ending", "Style adherence"]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".phase0/listening/kit-1")
    args = parser.parse_args()
    import numpy as np
    import soundfile as sf
    kit = args.output.resolve()
    kit.mkdir(parents=True, exist_ok=False)
    key = {"schemaVersion": 1, "engines": ENGINES, "pairs": {}}
    sheet = ["# Blind listening sheet", "",
             "Listen to each pair without opening `KEY-open-after-scoring.json`.",
             "For every criterion give each clip pass / minor / major / fail, then a",
             "preference (A, B, or none) and notes. Clips are 48 kHz stereo float WAV.", "",
             "Reviewer:", "Date:", "Playback device:", ""]
    for fixture, sources in PAIRS.items():
        order = ["reference", "candidate"]
        if secrets.randbelow(2):
            order.reverse()
        key["pairs"][fixture] = {}
        request = json.loads((ROOT / f"tools/phase0/requests/{fixture}.json").read_text(encoding="utf-8"))
        sheet += [f"## {fixture.capitalize()} fixture", "", f"Style: {request['style']}", "", "Lyrics:", "", "```",
                  request["lyrics"], "```", "", "| Criterion | A | B |", "| --- | --- | --- |"]
        sheet += [f"| {c} |  |  |" for c in CRITERIA]
        sheet += ["", "Preference (A / B / none):", "", "Notes:", ""]
        for label, engine in zip("AB", order):
            source = sources[engine]
            target = kit / f"{fixture}-{label}.wav"
            audio, rate = sf.read(source, dtype="float32", always_2d=True)
            sf.write(target, audio, rate, subtype="FLOAT", format="WAV")
            check, _ = sf.read(target, dtype="float32", always_2d=True)
            assert np.array_equal(audio, check), "Samples changed while rewriting"
            key["pairs"][fixture][label] = {"engine": engine, "source": str(source.relative_to(ROOT)).replace("\\", "/"),
                                            "sourceSha256": digest(source),
                                            "clipSha256": digest(target)}
    stamp = time.time()
    for clip in kit.glob("*.wav"):
        os.utime(clip, (stamp, stamp))
    (kit / "SCORING-SHEET.md").write_text("\n".join(sheet) + "\n", encoding="utf-8")
    (kit / "KEY-open-after-scoring.json").write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    print(f"Kit written to {kit}")


if __name__ == "__main__":
    main()
