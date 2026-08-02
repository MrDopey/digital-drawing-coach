#!/usr/bin/env python3
"""Bump pyproject.toml's [project].version by patch, minor, or major."""
import re
import sys
import tomllib
from pathlib import Path

VALID_BUMPS = ("patch", "minor", "major")


def bump(version: str, kind: str) -> str:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError(
            f"Current version {version!r} is not valid semver (MAJOR.MINOR.PATCH)"
        )

    major, minor_, patch = (int(part) for part in match.groups())
    if kind == "major":
        major, minor_, patch = major + 1, 0, 0
    elif kind == "minor":
        minor_, patch = minor_ + 1, 0
    elif kind == "patch":
        patch += 1
    else:
        raise ValueError(f"Unknown bump kind {kind!r}; expected one of {VALID_BUMPS}")

    return f"{major}.{minor_}.{patch}"


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in VALID_BUMPS:
        print(f"Usage: bump_version.py <{'|'.join(VALID_BUMPS)}>", file=sys.stderr)
        sys.exit(1)

    repo_root = Path(__file__).parent.parent
    pyproject = repo_root / "pyproject.toml"
    text = pyproject.read_text()
    current = tomllib.loads(text)["project"]["version"]

    try:
        new_version = bump(current, sys.argv[1])
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    updated_text, count = re.subn(
        r'(?m)^(version\s*=\s*)"' + re.escape(current) + r'"',
        rf'\g<1>"{new_version}"',
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError(
            f'Could not find version = "{current}" line in pyproject.toml'
        )

    pyproject.write_text(updated_text)
    print(new_version)


if __name__ == "__main__":
    main()
