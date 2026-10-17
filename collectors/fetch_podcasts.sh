#!/usr/bin/env bash
set -u; ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"; RUN_DIR="${1:-}"
[[ -d "$RUN_DIR" ]] || exit 2
python3 -c 'import sys; sys.path.insert(0,"lib"); import pipeline; [print(pipeline.dump(x)) for x in pipeline.feed_candidates(sys.argv[1],"podcast")]' "$RUN_DIR"
