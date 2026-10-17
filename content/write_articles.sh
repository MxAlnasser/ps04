#!/usr/bin/env bash
set -u; ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"; python3 lib/stages.py content "${1:-}"
python3 - "${1:-}" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1])/'articles.jsonl'
if p.exists(): print(p.read_text(),end='')
PY
