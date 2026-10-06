#!/usr/bin/env python3
"""Validate every skills/<name>/SKILL.md against the CONTRIBUTING.md schema.

Checks, per skill:
  - SKILL.md exists and has YAML frontmatter (--- ... ---)
  - frontmatter `name` is present and matches the directory name
  - frontmatter `description` is present and non-trivial
  - no hardcoded personal/machine-specific absolute paths (/home/<user>/...)

Exits non-zero (and prints every failure) if anything is wrong, so this can run as-is in CI.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
# Matches /home/<user>/... — a personal path that should be written `~`-relative instead.
HOME_PATH_RE = re.compile(r"/home/[a-zA-Z0-9_.-]+")


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def check_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        return [f"{skill_dir.name}: missing SKILL.md"]

    text = skill_md.read_text(encoding="utf-8")
    fields = parse_frontmatter(text)

    if not fields:
        errors.append(f"{skill_dir.name}: SKILL.md has no YAML frontmatter")
        return errors

    name = fields.get("name")
    if not name:
        errors.append(f"{skill_dir.name}: frontmatter missing `name`")
    elif name != skill_dir.name:
        errors.append(
            f"{skill_dir.name}: frontmatter name '{name}' does not match directory name"
        )

    description = fields.get("description", "")
    if not description or len(description) < 20:
        errors.append(f"{skill_dir.name}: frontmatter `description` is missing or too short")

    for md_file in skill_dir.rglob("*.md"):
        rel = md_file.relative_to(REPO_ROOT)
        content = md_file.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(content.splitlines(), start=1):
            if HOME_PATH_RE.search(line):
                errors.append(
                    f"{rel}:{lineno}: hardcoded personal path - use `~` "
                    f"(home-relative) instead: {line.strip()[:100]}"
                )

    return errors


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"No skills/ directory found at {SKILLS_DIR}", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    for skill_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        all_errors.extend(check_skill(skill_dir))

    if all_errors:
        print(f"skill-lint: {len(all_errors)} issue(s) found\n")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print(f"skill-lint: all {sum(1 for p in SKILLS_DIR.iterdir() if p.is_dir())} skills OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
