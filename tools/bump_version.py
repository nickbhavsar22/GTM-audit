#!/usr/bin/env python3
"""Bump the project version.

Usage:
    python tools/bump_version.py [major|minor|patch]

Defaults to 'patch' if no argument is given.
"""
import sys
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"


def bump(part: str = "patch") -> str:
    current = VERSION_FILE.read_text().strip()
    major, minor, patch = (int(x) for x in current.split("."))

    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    elif part == "patch":
        patch += 1
    else:
        print(f"Unknown bump type: {part}. Use major, minor, or patch.")
        sys.exit(1)

    version = f"{major}.{minor}.{patch}"
    VERSION_FILE.write_text(version + "\n")
    print(f"{current} -> {version}")
    return version


if __name__ == "__main__":
    bump(sys.argv[1] if len(sys.argv) > 1 else "patch")
