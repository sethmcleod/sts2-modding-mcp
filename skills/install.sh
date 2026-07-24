#!/usr/bin/env bash
# Install the shared STS2 modding skills into ~/.claude/skills/.
# Symlinks keep the skills in sync with this checkout. Run again after a pull
# only if a new skill directory appeared; edits to existing skills need no
# reinstall.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

mkdir -p "$DEST"

installed=0
for dir in "$SRC"/*/; do
  name="$(basename "$dir")"
  link="$DEST/$name"
  if [ -e "$link" ] && [ ! -L "$link" ]; then
    echo "skip  $name (a real directory already exists at $link)"
    continue
  fi
  ln -sfn "${dir%/}" "$link"
  echo "link  $name -> ${dir%/}"
  installed=$((installed + 1))
done

echo "Installed $installed skill(s) into $DEST"
