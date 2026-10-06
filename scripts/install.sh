#!/usr/bin/env bash
# Link every skills/<name> in this repo into a local agent's skill directory,
# so edits made here are picked up immediately without copying files around.
#
# Usage:
#   ./scripts/install.sh                       # links into ~/.claude/skills (Claude Code)
#   ./scripts/install.sh --target ~/.other-agent/skills
#   ./scripts/install.sh --copy                # copy instead of symlink (e.g. read-only home dirs)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${HOME}/.claude/skills"
MODE="link"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --copy) MODE="copy"; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

mkdir -p "$TARGET"

for skill_dir in "$REPO_ROOT"/skills/*/; do
  name="$(basename "$skill_dir")"
  dest="$TARGET/$name"

  if [[ -e "$dest" || -L "$dest" ]]; then
    echo "skip (exists): $name"
    continue
  fi

  if [[ "$MODE" == "copy" ]]; then
    cp -r "$skill_dir" "$dest"
    echo "copied: $name"
  else
    ln -s "$skill_dir" "$dest"
    echo "linked: $name -> $skill_dir"
  fi
done

echo "Done. Skills available under: $TARGET"
