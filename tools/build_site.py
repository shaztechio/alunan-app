#!/usr/bin/env python3
"""Assemble the alunan.app GitHub Pages artifact from its public docs/ files.

Only the landing page, its assets, CNAME and .nojekyll are published. The rest
of docs/ (decisions, validation evidence) stays on GitHub, not on the website.
"""

import argparse
from pathlib import Path
import shutil

DOMAIN = "alunan.app"
PUBLIC_FILES = ("index.html", "CNAME", ".nojekyll")


def build(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output == source or source in output.parents:
        raise ValueError("Build output must be outside the docs source directory")
    if (source / "CNAME").read_text(encoding="utf-8").strip() != DOMAIN:
        raise ValueError(f"CNAME must contain {DOMAIN}")
    html = (source / "index.html").read_text(encoding="utf-8")
    if "{{" in html:
        raise ValueError("Unresolved template placeholder")
    if f'<link rel="canonical" href="https://{DOMAIN}/">' not in html:
        raise ValueError("Canonical URL must use the custom domain")
    output.mkdir(parents=True, exist_ok=True)
    for name in PUBLIC_FILES:
        shutil.copyfile(source / name, output / name)
    if (source / "assets").is_dir():
        shutil.copytree(source / "assets", output / "assets", dirs_exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        build(args.source, args.output)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Site build failed: {error}\n")
    print(f"Site built for {DOMAIN} in {args.output}")


if __name__ == "__main__":
    main()
