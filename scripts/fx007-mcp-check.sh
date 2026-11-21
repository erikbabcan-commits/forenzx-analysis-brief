#!/usr/bin/env bash
# Optional real-process integration check; separate from the offline product tests.
# Add --with-codex to require a named AI client, --with-legacy-sdk for a diagnostic.
set -euo pipefail
forenzx_project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$forenzx_project_root"
forenzx_upstream_commit='0e4c7fae5944d44c1746ab3101acfbd70ab1ab8f'
forenzx_runtime="$forenzx_project_root/.fx007-runtime"
forenzx_upstream="$forenzx_runtime/upstream"
forenzx_python="$forenzx_runtime/venv/bin/python"

for command_name in git python3; do
  command -v "$command_name" >/dev/null 2>&1 || { printf 'Missing prerequisite: %s\n' "$command_name" >&2; exit 1; }
done
python3 -c 'import sys; sys.exit("ForenZX server requires Python 3.11+" if sys.version_info < (3,11) else 0)'
for argument in "$@"; do
  case "$argument" in
    --with-codex)
      command -v codex >/dev/null 2>&1 || { echo 'Install and sign in to Codex CLI before using --with-codex.' >&2; exit 1; }
      ;;
    --with-legacy-sdk) ;;
    *) printf 'Supported options: --with-codex --with-legacy-sdk. Unexpected: %s\n' "$argument" >&2; exit 1 ;;
  esac
done

mkdir -p "$forenzx_runtime"
if [ ! -e "$forenzx_upstream" ]; then
  git clone 'https://github.com/erikbabcan-commits/forenzx-mcp-hub.git' "$forenzx_upstream"
  git -C "$forenzx_upstream" checkout --detach "$forenzx_upstream_commit"
fi
if [ "$(git -C "$forenzx_upstream" rev-parse HEAD)" != "$forenzx_upstream_commit" ]; then
  echo 'Existing upstream checkout is at a different commit; nothing was reset.' >&2
  exit 1
fi
if [ -n "$(git -C "$forenzx_upstream" status --porcelain)" ]; then
  echo 'Upstream checkout has local changes; preserve them and use a clean pinned checkout.' >&2
  exit 1
fi

if [ ! -x "$forenzx_python" ]; then
  python3 -m venv "$forenzx_runtime/venv"
fi
"$forenzx_python" -m pip install -r scripts/requirements-fx007.txt
forenzx_run_name="$(python3 -c 'from datetime import datetime,timezone; from uuid import uuid4; print(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid4().hex[:8])')"
forenzx_report="$forenzx_runtime/runs/$forenzx_run_name"
printf '\nSynthetic integration report directory: %s\n' "$forenzx_report"
exec "$forenzx_python" integration/fx007/run_probe.py \
  --upstream "$forenzx_upstream" --output "$forenzx_report" "$@"
