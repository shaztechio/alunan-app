"""Regression tests for tools/build_site.py."""

from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_site  # noqa: E402

DOCS = Path(__file__).resolve().parents[1] / "docs"


class BuildSiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temp)

    def copy_docs(self):
        source = self.temp / "docs"
        source.mkdir()
        for name in build_site.PUBLIC_FILES:
            shutil.copyfile(DOCS / name, source / name)
        return source

    def test_publishes_only_public_files(self):
        output = self.temp / "site"
        build_site.build(DOCS, output)
        self.assertEqual({p.name for p in output.iterdir()}, set(build_site.PUBLIC_FILES))
        self.assertEqual((output / "CNAME").read_text(encoding="utf-8").strip(), "alunan.app")

    def test_rejects_output_inside_source(self):
        with self.assertRaises(ValueError):
            build_site.build(DOCS, DOCS / "_site")

    def test_rejects_wrong_domain(self):
        source = self.copy_docs()
        (source / "CNAME").write_text("example.com\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            build_site.build(source, self.temp / "site")

    def test_rejects_placeholder(self):
        source = self.copy_docs()
        page = source / "index.html"
        page.write_text(page.read_text(encoding="utf-8") + "{{VERSION}}", encoding="utf-8")
        with self.assertRaises(ValueError):
            build_site.build(source, self.temp / "site")


if __name__ == "__main__":
    unittest.main()
