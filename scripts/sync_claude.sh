#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

src="$repo_root/claude-code/claude/"
dest="$repo_root/.claude/"

if [[ ! -d "$src" ]]; then
  echo "Missing source folder: $src" >&2
  exit 1
fi

rsync -a "$src" "$dest"

echo "Synced $src -> $dest"
