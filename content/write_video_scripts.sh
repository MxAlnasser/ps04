#!/usr/bin/env bash
set -u; ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"; python3 - <<'PY' "${1:-}"
import sys
sys.path.insert(0,'lib'); import stages
stages.write_content(sys.argv[1])
PY
cat "${1:-}/video_scripts.jsonl"
