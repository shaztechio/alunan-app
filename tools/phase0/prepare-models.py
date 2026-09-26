"""Cross-platform research equivalent of prepare-models.ps1 (macOS, Linux, Windows).

Developer research tool, not the application's model downloader. Downloads one
pinned profile from model-profiles.lock.json with curl, keeping partial files
as <name>.incomplete and resuming them, then promotes each file only after its
size and SHA-256 match the lock. Existing verified files are not downloaded again.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs/validation/phase0/model-profiles.lock.json"
DESTINATION = ROOT / ".phase0/models"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="yue2-cpp-q8", choices=["yue2-reference-bf16", "yue2-cpp-q8"])
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text(encoding="utf-8-sig"))
    profile = next(p for p in lock["profiles"] if p["id"] == args.profile)
    for asset in profile["assets"]:
        relative = PurePosixPath(asset["repository"], asset["revision"], asset["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise SystemExit("Unsafe asset path")
        expected_url = f"https://huggingface.co/{asset['repository']}/resolve/{asset['revision']}/{asset['path']}"
        if asset["url"] != expected_url:
            raise SystemExit("Unexpected source URL")
        target = DESTINATION.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.stat().st_size == asset["bytes"] and digest(target) == asset["sha256"]:
            print(f"Verified existing {asset['path']}")
            continue
        partial = target.with_name(target.name + ".incomplete")
        print(f"Downloading {asset['path']} ({asset['bytes']} bytes)", flush=True)
        subprocess.run(["curl", "-fL", "--retry", "3", "--continue-at", "-", "-o", str(partial), asset["url"]], check=True)
        if partial.stat().st_size != asset["bytes"] or digest(partial) != asset["sha256"]:
            raise SystemExit(f"Verification failed for {asset['path']}; partial kept at {partial}")
        partial.replace(target)
        print(f"Verified {asset['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
