#!/bin/bash
# Create a new URP project with the actual editor and an explicit template archive.
# Usage: bash create_urp.sh EDITOR TEMPLATE NEW_PROJECT LOG
# Tested: Unity 6000.6.5f1, urp-blank template 17.2.1, macOS arm64.
set -euo pipefail

if [ "$#" -ne 4 ]; then
  printf 'Usage: bash create_urp.sh EDITOR TEMPLATE NEW_PROJECT LOG\n' >&2
  exit 2
fi
EDITOR="$1"
TEMPLATE="$2"
PROJECT="$3"
LOG="$4"
if [ ! -x "$EDITOR" ] || [ ! -f "$TEMPLATE" ]; then
  printf 'Supply the editor executable and an existing URP template archive.\n' >&2
  exit 1
fi
if [ -e "$PROJECT" ]; then
  printf 'Refusing to create over an existing project: %s\n' "$PROJECT" >&2
  exit 1
fi
mkdir -p "$(dirname "$PROJECT")" "$(dirname "$LOG")"
exec "$EDITOR" -batchmode -quit -createProject "$PROJECT" \
  -cloneFromTemplate "$TEMPLATE" -logFile "$LOG"
