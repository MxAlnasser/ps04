#!/usr/bin/env bash
set -u; ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"; python3 lib/stages.py summary "${1:-}"
