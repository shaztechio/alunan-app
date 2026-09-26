"""Install the recorded Windows reference environment from its hash lock.

Developer research tool. Creates a new venv (refusing to reuse an existing
directory), installs every locked wheel with --require-hashes and --no-deps,
then installs the pinned YuE2 source tree without dependency resolution.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs/validation/phase0/windows-python-packages.lock.json"
PINS = ROOT / "docs/validation/phase0/source-pins.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--venv", default=".phase0/reference-venv")
    args = parser.parse_args()
    venv = (ROOT / args.venv).resolve()
    if venv.exists():
        raise SystemExit(f"Refusing to reuse existing environment: {venv}")
    lock = json.loads(LOCK.read_text(encoding="utf-8-sig"))
    if sys.version.split()[0] != lock["python"]:
        raise SystemExit(f"Expected Python {lock['python']}, running {sys.version.split()[0]}")
    commit = next(s["commit"] for s in json.loads(PINS.read_text(encoding="utf-8-sig"))["sources"] if s["id"] == "yue2")
    if commit != lock["engineSource"]:
        raise SystemExit("Package lock and source pin disagree")
    source = ROOT / ".phase0/yue2" / f"YuE-{commit}"
    if not (source / "pyproject.toml").exists() and not (source / "setup.py").exists():
        raise SystemExit(f"Pinned YuE2 source not extracted at {source}")

    requirements = venv.parent / f"{venv.name}.requirements.txt"
    lines = [f"{p['name']} @ {p['url']} --hash=sha256:{p['sha256']}" for p in lock["packages"]]
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    requirements.write_text("\n".join(lines) + "\n", encoding="utf-8")
    python = venv / "Scripts/python.exe"
    subprocess.run([str(python), "-m", "pip", "install", "--no-deps", "--require-hashes",
                    "--only-binary", ":all:", "-r", str(requirements)], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--no-deps", "--no-build-isolation", str(source)], check=True)
    subprocess.run([str(python), "-m", "pip", "check"], check=True)
    subprocess.run([str(python), str(ROOT / "tools/phase0/validate-locks.py")], check=True)


if __name__ == "__main__":
    main()
