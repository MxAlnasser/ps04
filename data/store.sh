#!/usr/bin/env bash
set -u; ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
case "${1:-}" in
	init) python3 -c 'import sys;sys.path.insert(0,"lib");import pipeline;pipeline.db().close()' ;;
	upsert) python3 lib/pipeline.py upsert "${2:-}" ;;
	list) python3 lib/pipeline.py list ;;
	get) python3 - "$2" "${3:-}" <<'PY'
import sys; sys.path.insert(0,'lib'); import pipeline
con=pipeline.db(); q='SELECT record FROM versions WHERE item_id=?'; args=[sys.argv[1]]
if sys.argv[2]: q+=' AND version_id=?'; args.append(sys.argv[2])
r=con.execute(q+' ORDER BY rowid DESC LIMIT 1',args).fetchone(); con.close()
if not r: raise SystemExit(1)
print(r[0])
PY
	;;
	*) echo 'usage: init|upsert RUN_DIR|list|get ITEM_ID [VERSION_ID]' >&2; exit 2;;
esac
