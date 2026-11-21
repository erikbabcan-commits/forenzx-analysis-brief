#!/usr/bin/env bash
set -euo pipefail

# Run from this checkout, even when invoked from a different directory.
forenzx_project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$forenzx_project_root"

if ! command -v node >/dev/null 2>&1; then
  echo "ForenZX needs Node.js 22.13.0 or newer. Install Node, then rerun this script." >&2
  exit 1
fi

# The Node supervisor validates prerequisites and owns every child process.
# exec ensures Ctrl+C/SIGTERM reaches that supervisor directly.
exec node scripts/local-dashboard.mjs --bootstrap "$@"
