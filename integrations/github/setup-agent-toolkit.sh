#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
case "${1:-}" in
  '') runtime=yes ;;
  --skills-only) runtime=no ;;
  *) echo 'Usage: bash tools/setup-agent-toolkit.sh [--skills-only]' >&2; exit 2 ;;
esac
git submodule update --init -- .agent-toolkit
python3 .agent-toolkit/scripts/toolkit.py install --project "$project_root"
python3 .agent-toolkit/scripts/toolkit.py emit-routes --project "$project_root" --agents claude
if [ "$runtime" = yes ]; then
  python3 .agent-toolkit/scripts/toolkit.py setup-runtime --project "$project_root"
  python3 .agent-toolkit/scripts/toolkit.py verify-runtime --project "$project_root"
fi
python3 .agent-toolkit/scripts/toolkit.py verify --project "$project_root"
