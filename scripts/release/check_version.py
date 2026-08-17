"""Validate the repository release-version contract.

The root VERSION file is canonical.  Other version declarations that belong to
this repository must display the same value so a release can be identified
consistently in source, documentation, and dbt metadata.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
DBT_VERSION_PATTERN = re.compile(r"^version:\s*['\"]?([^'\"\s#]+)", re.MULTILINE)
README_VERSION_PATTERN = re.compile(
    r"^> \*\*Repository version:\*\* `([^`]+)`", re.MULTILINE
)


def _read_version(path: Path, pattern: re.Pattern[str] | None = None) -> str | None:
    if not path.is_file():
        return None

    content = path.read_text(encoding="utf-8")
    if pattern is None:
        return content.strip()

    match = pattern.search(content)
    return match.group(1) if match else None


def validate_version(repo_root: Path) -> list[str]:
    """Return release-version contract violations for ``repo_root``."""
    root = repo_root.resolve()
    canonical = _read_version(root / "VERSION")
    if canonical is None:
        return ["VERSION is missing."]
    if not SEMVER_PATTERN.fullmatch(canonical):
        return [f"VERSION must use MAJOR.MINOR.PATCH; found {canonical!r}."]

    declarations = (
        (root / "README.md", README_VERSION_PATTERN),
        (root / "warehouse" / "dbt_project.yml", DBT_VERSION_PATTERN),
    )
    errors: list[str] = []
    for path, pattern in declarations:
        declared = _read_version(path, pattern)
        label = path.relative_to(root).as_posix()
        if declared is None:
            errors.append(f"{label} has no readable release version.")
        elif declared != canonical:
            errors.append(
                f"{label} declares {declared!r}, but VERSION declares {canonical!r}."
            )
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    errors = validate_version(repo_root)
    if errors:
        print("Release-version check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Release-version check passed: {_read_version(repo_root / 'VERSION')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
