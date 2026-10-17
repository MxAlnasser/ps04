#!/usr/bin/env bash
set -u; ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"; RUN_DIR="${1:-}"; [[ -d "$RUN_DIR" ]] || exit 2
status=0
log() { printf '[collect] %s\n' "$*" >&2; }
log "fetching RSS feeds"
timeout -k 5 120 bash collectors/fetch_feeds.sh "$RUN_DIR" > "$RUN_DIR/candidates/feeds.jsonl" || { log "RSS collection failed or timed out"; status=1; }
log "fetching YouTube sources"
timeout -k 5 120 bash collectors/fetch_youtube.sh "$RUN_DIR" > "$RUN_DIR/candidates/youtube.jsonl" || { log "YouTube collection failed or timed out"; status=1; }
log "fetching podcast sources"
timeout -k 5 120 bash collectors/fetch_podcasts.sh "$RUN_DIR" > "$RUN_DIR/candidates/podcasts.jsonl" || { log "podcast collection failed or timed out"; status=1; }
cat "$RUN_DIR/candidates/feeds.jsonl" "$RUN_DIR/candidates/youtube.jsonl" "$RUN_DIR/candidates/podcasts.jsonl" > "$RUN_DIR/candidates.jsonl"
log "extracting content and transcripts"
timeout -k 5 360 bash processing/extract_content.sh "$RUN_DIR" < "$RUN_DIR/candidates.jsonl" > "$RUN_DIR/items.jsonl" || { log "extraction failed or timed out"; status=1; }
log "updating evidence store"
bash data/store.sh upsert "$RUN_DIR" < "$RUN_DIR/items.jsonl" > "$RUN_DIR/changes.jsonl" || status=1
bash data/store.sh list > "$RUN_DIR/corpus.jsonl" || status=1
log "applying freshness filter"
bash processing/filter_items.sh "$RUN_DIR" < "$RUN_DIR/corpus.jsonl" > "$RUN_DIR/eligible.jsonl" || status=1
exit "$status"
