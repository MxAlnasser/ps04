#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"; cd "$ROOT"
log() { printf '[run] %s\n' "$*" >&2; }
usage() {
	cat >&2 <<'EOF'
Usage:
  ./run.sh              Fetch the latest configured news and build a series.
  ./run.sh --full       Also use Whisper when media has no automatic captions.
  ./run.sh --offline    Run without Codex for a fast local check.
	./run.sh --voiceovers Generate voice audio from the current Google Vids prompts.
  ./run.sh --package RUN_DIR
                       Package a reviewed run for publication.

Reviewable files are refreshed under output/. Machine-readable run data is saved under runs/RUN_ID/.
EOF
}
MODE="normal"
OUTPUT_MODE="full"
VOICEOVERS=0
choose_output() {
	if ! command -v gum >/dev/null 2>&1; then
		printf 'Choose output (1=full, 2=prompts, 3=articles): ' >&2
		read -r choice
	else
		choice="$(gum choose --header='What should be generated?' \
			'Full package: articles + Google Vids prompts + voiceovers' \
			'Articles + Google Vids prompts' \
			'Articles only')"
	fi
	case "$choice" in
		'Full package'*|1) OUTPUT_MODE="full"; VOICEOVERS=1 ;;
		'Articles + Google Vids prompts'|2) OUTPUT_MODE="prompts" ;;
		'Articles only'|3) OUTPUT_MODE="articles" ;;
		*) log 'No choice made; using articles + Google Vids prompts.'; OUTPUT_MODE="prompts" ;;
	esac
}
case "${1:-}" in
	--help|-h) usage; exit 0 ;;
	--full) MODE="full"; export PIPELINE_ALLOW_WHISPER=1; shift ;;
	--offline) MODE="offline"; export PIPELINE_USE_CODEX=0; shift ;;
	--voiceovers) python3 lib/generate_voiceovers.py; exit $? ;;
	--package) ;;
esac
if [[ "${1:-}" == "--package" ]]; then
	RUN_DIR="${2:-}"; [[ -d "$RUN_DIR" ]] || { echo "missing run directory" >&2; exit 2; }
	log "checking package inputs in $RUN_DIR"
	bash review/check_content.sh "$RUN_DIR" > "$RUN_DIR/review.json" || true
	log "preparing publication package"
	bash publishing/prepare_package.sh "$RUN_DIR" || exit $?
	python3 lib/stages.py summary "$RUN_DIR" | tee "$RUN_DIR/summary.json"; exit 0
fi
[[ $# -eq 0 ]] || { usage; exit 2; }
choose_output
export OUTPUT_MODE
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"; RUN_DIR="$ROOT/runs/$RUN_ID"
log "starting $MODE run $RUN_ID"
mkdir -p "$RUN_DIR/config" "$RUN_DIR/prompts" "$RUN_DIR/logs" "$RUN_DIR/candidates"
cp config/project.json config/sources.json config/editorial_policy.md "$RUN_DIR/config/"
cp prompts/*.md "$RUN_DIR/prompts/"
printf '{"run_id":"%s","started_at":"%s","as_of_date":"%s","mode":"live","previous_run_id":null}\n' "$RUN_ID" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(date -u +%Y-%m-%d)" > "$RUN_DIR/run.json"
bash data/store.sh init
pipeline_status=0
log "collecting and filtering sources"
timeout -k 5 600 bash workflows/collect_sources.sh "$RUN_DIR" || { log "collection finished with errors or timeout"; pipeline_status=1; }
log "creating editorial series"
timeout -k 5 300 bash workflows/create_series.sh "$RUN_DIR" || { log "series finished with errors or timeout"; pipeline_status=1; }
log "writing run summary"
python3 lib/stages.py summary "$RUN_DIR" > "$RUN_DIR/summary.json"
python3 lib/stages.py handoff "$RUN_DIR" >/dev/null
if [[ "$VOICEOVERS" -eq 1 ]]; then
	log 'generating voiceovers with voice.wav'
	timeout -k 10 900 python3 lib/generate_voiceovers.py || { log 'voiceover generation failed or timed out'; pipeline_status=1; }
fi
printf '\nYour review files are ready in one place:\n'
printf '  Output folder:    output/\n'
printf '  Friendly guide:   output/README.md\n'
printf '  Articles:         output/articles/\n'
printf '  Google Vids:      output/google-vids/\n'
printf '  Source lists:     output/sources/\n'
printf '  Downloaded media: output/media/\n'
log "finished; artifacts are in $RUN_DIR"
exit "$pipeline_status"
