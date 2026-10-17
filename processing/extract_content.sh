#!/usr/bin/env bash
set -u; ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"; RUN_DIR="${1:-}"
[[ -d "$RUN_DIR" ]] || exit 2
python3 lib/pipeline.py extract "$RUN_DIR"
