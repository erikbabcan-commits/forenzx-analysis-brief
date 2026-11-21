#!/usr/bin/env bash
# Clone once into a new directory, then verify and run the local dashboard.
# Usage: bash clone-and-test.sh [destination] [--check-only] [--port N]
set -euo pipefail

repo='erikbabcan-commits/forenzx-analysis-brief'
destination='forenzx-analysis-brief'
if [ "$#" -gt 0 ] && [[ "$1" != --* ]]; then
  destination="$1"
  shift
fi

for command_name in git node npm python3; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'Missing prerequisite: %s. Install Node 22.13+, Python 3.10+ and Git first.\n' "$command_name" >&2
    exit 1
  fi
done
node -e 'const [major, minor] = process.versions.node.split(".").map(Number); if (major < 22 || (major === 22 && minor < 13)) { console.error("Node 22.13+ required"); process.exit(1); }'
python3 -c 'import sys; sys.exit("Python 3.10+ required" if sys.version_info < (3,10) else 0)'

case "$destination" in
  /*) ;;
  *) destination="$PWD/$destination" ;;
esac
if [ -e "$destination" ] || [ -L "$destination" ]; then
  printf 'Destination already exists; nothing was changed: %s\n' "$destination" >&2
  printf 'For an existing checkout, run: bash scripts/local-bootstrap.sh\n' >&2
  exit 1
fi

if command -v gh >/dev/null 2>&1 && gh auth status --hostname github.com >/dev/null 2>&1; then
  gh repo clone "$repo" "$destination"
else
  # Uses your existing Git credential helper. No credential is embedded here.
  git clone "https://github.com/$repo.git" "$destination"
fi

cd "$destination"
printf '\nChecked out commit: '
git rev-parse HEAD
exec bash scripts/local-bootstrap.sh "$@"
