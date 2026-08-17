"""Tests for the repository release-version consistency check."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from check_version import validate_version


class ValidateVersionTests(unittest.TestCase):
    def _write_release_files(
        self, root: Path, *, version: str = "1.0.0", dbt_version: str = "1.0.0"
    ) -> None:
        (root / "VERSION").write_text(f"{version}\n", encoding="utf-8")
        (root / "README.md").write_text(
            f"# Example\n\n> **Repository version:** `{version}`\n",
            encoding="utf-8",
        )
        warehouse = root / "warehouse"
        warehouse.mkdir()
        (warehouse / "dbt_project.yml").write_text(
            f"name: 'example'\nversion: '{dbt_version}'\n", encoding="utf-8"
        )

    def test_accepts_matching_semantic_versions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_release_files(root)

            self.assertEqual(validate_version(root), [])

    def test_reports_version_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_release_files(root, dbt_version="1.0.1")

            errors = validate_version(root)

            self.assertTrue(any("warehouse/dbt_project.yml" in error for error in errors))

    def test_rejects_non_semantic_root_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_release_files(root, version="1.0")

            errors = validate_version(root)

            self.assertTrue(any("MAJOR.MINOR.PATCH" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
