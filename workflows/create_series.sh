#!/usr/bin/env bash
set -u; ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"; RUN_DIR="${1:-}"; [[ -d "$RUN_DIR" ]] || exit 2
status=0
log() { printf '[series] %s\n' "$*" >&2; }
log "selecting editorial items"
bash editorial/select_items.sh "$RUN_DIR" < "$RUN_DIR/eligible.jsonl" > "$RUN_DIR/decisions.jsonl" || status=1
log "creating three editorial briefs"
bash editorial/create_briefs.sh "$RUN_DIR" < "$RUN_DIR/decisions.jsonl" > "$RUN_DIR/briefs.jsonl" || status=1
log "writing article drafts"
bash content/write_articles.sh "$RUN_DIR" < "$RUN_DIR/briefs.jsonl" > /dev/null || status=1
log "converting articles to video scripts"
bash content/write_video_scripts.sh "$RUN_DIR" < "$RUN_DIR/briefs.jsonl" > /dev/null || status=1
log "checking generated content"
bash review/check_content.sh "$RUN_DIR" > "$RUN_DIR/review.json" || status=1
exit "$status"
