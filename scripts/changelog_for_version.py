"""Extract a single version's section from CHANGELOG.md.

Used by the release workflow to fill the GitHub Release body with the matching
changelog, so every release always carries human-written notes.

Usage:
    python scripts/changelog_for_version.py 0.1.5        # print section (Markdown)
    python scripts/changelog_for_version.py v0.1.5       # 'v' prefix is fine too
    python scripts/changelog_for_version.py 0.1.5 --file CHANGELOG.md

Exit codes:
    0  section found and printed
    1  version not found in the changelog
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Matches a heading like:  ## [0.1.5] — 2026-01-XX   or   ## [0.1.5]
_HEADING = re.compile(r"^##\s+\[(?P<version>[^\]]+)\][^\n]*$", re.MULTILINE)


def extract(changelog_text: str, version: str) -> str | None:
    """Return the body (without the heading line) for `version`, or None."""
    version = version.strip().lstrip("vV")
    matches = list(_HEADING.finditer(changelog_text))
    for i, m in enumerate(matches):
        if m.group("version").strip().lstrip("vV") != version:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(changelog_text)
        body = changelog_text[start:end].strip()
        return body or None
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Version to extract, e.g. 0.1.5 or v0.1.5")
    parser.add_argument("--file", default="CHANGELOG.md", help="Path to the changelog")
    args = parser.parse_args(argv)

    path = Path(args.file)
    if not path.exists():
        print(f"error: {path} not found", file=sys.stderr)
        return 1

    body = extract(path.read_text(encoding="utf-8"), args.version)
    if body is None:
        print(f"error: no changelog section for {args.version}", file=sys.stderr)
        return 1

    version = args.version.strip().lstrip("vV")
    print(f"## What's changed in v{version}\n")
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
