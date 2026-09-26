"""Offline structural checks for Phase 0 research locks and input fixtures."""
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[2]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    source_ids = set()
    for source in read("docs/validation/phase0/source-pins.json")["sources"]:
        require(source["id"] not in source_ids, "Duplicate source id")
        source_ids.add(source["id"])
        require(re.fullmatch("[0-9a-f]{40}", source["commit"]), "Unpinned source")
        require(re.fullmatch("[0-9a-f]{64}", source["archiveSha256"]), "Missing archive digest")
        require(source["archiveUrl"].endswith(source["commit"]), "Archive revision mismatch")
    profile_ids = set()
    for profile in read("docs/validation/phase0/model-profiles.lock.json")["profiles"]:
        require(profile["id"] not in profile_ids, "Duplicate profile id")
        profile_ids.add(profile["id"])
        require(profile["engine"] in source_ids, "Unknown engine")
        require(profile["totalBytes"] == sum(a["bytes"] for a in profile["assets"]), "Incorrect profile size")
        identities = set()
        for asset in profile["assets"]:
            key = (asset["repository"], asset["revision"], asset["path"])
            require(key not in identities, "Duplicate asset")
            identities.add(key)
            require(re.fullmatch("[0-9a-f]{40}", asset["revision"]), "Unpinned model")
            require(re.fullmatch("[0-9a-f]{64}", asset["sha256"]), "Missing model digest")
            path = PurePosixPath(asset["path"])
            require(not path.is_absolute() and ".." not in path.parts and "\\" not in asset["path"], "Unsafe path")
            require(path.suffix not in {".py", ".whl", ".exe", ".dll"}, "Executable model-cache asset")
            require(asset["bytes"] > 0, "Invalid byte length")
            require(asset["url"] == f"https://huggingface.co/{asset['repository']}/resolve/{asset['revision']}/{asset['path']}", "Source mismatch")
    names = set()
    for package in read("docs/validation/phase0/windows-python-packages.lock.json")["packages"]:
        require(package["name"] not in names, "Duplicate package")
        names.add(package["name"])
        require(re.fullmatch("[0-9a-f]{64}", package["sha256"] or ""), "Missing package digest")
        require(package["url"].startswith("https://"), "Unexpected package source")
    for name in ("short", "full"):
        request = read(f"tools/phase0/requests/{name}.json")
        require(request["style"] and request["lyrics"], "Empty fixture")
        require(request["cot"] == "full" and isinstance(request["seed"], int), "Unexpected fixture settings")
    print(f"Validated {len(source_ids)} sources, {len(profile_ids)} profiles, {len(names)} packages, and 2 requests")


if __name__ == "__main__":
    main()
