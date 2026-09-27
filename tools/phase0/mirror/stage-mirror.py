"""Stage the Alunan model mirror upload set (research tool).

Hard-links the project's own Q8 conversion, the decoder, the original license
and notice files into .phase0/mirror-staging/<set>/, adds CONVERSION.md with LF
line endings, checks every file against the expected digests, and writes
SHA256SUMS. Uploading to Cloudflare R2 is a separate, owner-run step.
"""
import argparse
import hashlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
P0 = ROOT / ".phase0"
YUE = P0 / "models/m-a-p/YuE2-3B/14fc6c6f146441b1dd6363fcb2e01e82a6914cb7"
NOTE = ROOT / "tools/phase0/mirror/CONVERSION.md"
FILES = {
    "YuE2-3B-Q8_0.gguf": (P0 / "conversion/models/YuE2-3B-Q8_0.gguf",
                          "0d6ecb65cd27a20dd24e08ac46b99d0d991087782180399b532019c55c8759f7"),
    "YuE2-Vae-F32.gguf": (P0 / "conversion/models/YuE2-Vae-F32.gguf",
                          "93e49dfb1970e89ad64cacb17cf13b5d05f6bb30ef7ed3adae3050bcb728638a"),
    "LICENSE": (YUE / "LICENSE", "060985741d20e70613b4c189c7de106cabd3fb2109fbbfb6d705c9d619417dd0"),
    "THIRD_PARTY_NOTICES.md": (YUE / "THIRD_PARTY_NOTICES.md",
                               "14d3fd9f6fee86b4260b69b0979735b99ffec8c6b4db254567047a4215cd9af3"),
    "licenses/SnakeBeta-NVIDIA-MIT.txt": (YUE / "licenses/SnakeBeta-NVIDIA-MIT.txt",
                                          "da9858d516047d82096d01c112a61bd67f26d289039464d668a1d45f91738ecc"),
    "licenses/stable-audio-tools-MIT.txt": (YUE / "licenses/stable-audio-tools-MIT.txt",
                                            "a1fac33b7bcd791b74fb33aeb439f825e7277e239fc119fb7d2ab6f084a0c101"),
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", default="yue2-cpp-q8-v1")
    args = parser.parse_args()
    out = P0 / "mirror-staging" / args.set
    if out.exists():
        raise SystemExit(f"Refusing to reuse {out}")
    sums = []
    for name, (source, expected) in FILES.items():
        if digest(source) != expected:
            raise SystemExit(f"{source} does not match its expected digest")
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, target)
        sums.append(f"{expected}  {name}")
    note = out / "CONVERSION.md"
    lf = "\n"
    note.write_text(NOTE.read_text(encoding="utf-8").replace("\r" + lf, lf), encoding="utf-8", newline=lf)
    sums.append(f"{digest(note)}  CONVERSION.md")
    (out / "SHA256SUMS").write_text(lf.join(sums) + lf, encoding="utf-8", newline=lf)
    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"Staged {len(sums)} files, {total} bytes, in {out}")
    print((out / "SHA256SUMS").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
