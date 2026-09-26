"""Download, verify, and extract a pinned vendor GPU runtime pack (research tool).

Follows the FEATURES.md MOD-015 rules the app will implement: the archive must
match its pinned size and SHA-256 before it is opened; only allow-listed regular
files are extracted (links, duplicates, and unsafe names fail the pack); files
are written under their pinned names; per-file digests are checked when pinned
and otherwise recorded. Output: .phase0/runtime-packs/<id>/files/ and files.json.
Not the application's downloader.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs/validation/phase0/runtime-packs.lock.json"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe(name):
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in name and ":" not in name


def members(archive, fmt):
    """Yield (name, is_regular_file, opener) for every archive entry."""
    if fmt == "zip":
        z = zipfile.ZipFile(archive)
        for info in z.infolist():
            mode = (info.external_attr >> 16) & 0o170000
            regular = not info.is_dir() and mode in (0, 0o100000)
            yield info.filename, regular, (lambda i=info: z.open(i))
    else:
        t = tarfile.open(archive, "r:xz")
        for info in t:
            yield info.name, info.isreg(), (lambda i=info: t.extractfile(i))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", required=True)
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text(encoding="utf-8-sig"))
    pack = next(p for p in lock["packs"] if p["id"] == args.pack)
    folder = ROOT / ".phase0/runtime-packs" / pack["id"]
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / PurePosixPath(pack["url"]).name
    if not (archive.exists() and archive.stat().st_size == pack["bytes"] and digest(archive) == pack["sha256"]):
        partial = archive.with_name(archive.name + ".incomplete")
        print(f"Downloading {pack['url']} ({pack['bytes']} bytes)", flush=True)
        subprocess.run(["curl", "-fL", "--retry", "3", "--continue-at", "-", "-o", str(partial), pack["url"]], check=True)
        if partial.stat().st_size != pack["bytes"] or digest(partial) != pack["sha256"]:
            raise SystemExit(f"Archive verification failed; partial kept at {partial}")
        partial.replace(archive)
    print("Archive verified", flush=True)

    files = folder / "files"
    if files.exists():
        shutil.rmtree(files)
    files.mkdir()
    wanted = pack["files"]
    found = {f["name"]: [] for f in wanted}
    entries = 0
    for name, regular, opener in members(archive, pack["format"]):
        entries += 1
        if not safe(name):
            raise SystemExit(f"Unsafe archive entry: {name}")
        for f in wanted:
            match = name == f["member"] if "member" in f else re.fullmatch(f["memberPattern"], name)
            if match:
                if not regular:
                    raise SystemExit(f"Allow-listed entry is not a regular file: {name}")
                found[f["name"]].append(name)
                with opener() as src, (files / f["name"]).open("wb") as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
    record = {"pack": pack["id"], "archiveSha256": pack["sha256"], "archiveEntries": entries, "files": {}}
    for f in wanted:
        if len(found[f["name"]]) != 1:
            raise SystemExit(f"Expected exactly one archive entry for {f['name']}, found {found[f['name']]}")
        out = files / f["name"]
        size, sha = out.stat().st_size, digest(out)
        if f.get("sha256") and (sha != f["sha256"] or size != f["bytes"]):
            raise SystemExit(f"Extracted file does not match its pin: {f['name']}")
        record["files"][f["name"]] = {"member": found[f["name"]][0], "bytes": size, "sha256": sha,
                                      "pinned": bool(f.get("sha256"))}
    (folder / "files.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
