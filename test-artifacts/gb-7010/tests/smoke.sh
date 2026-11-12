#!/usr/bin/env bash
set -euo pipefail
BASE="${BACKEND_URL:-http://localhost:19209}"
LOG_DIR="${LOG_DIR:-$(pwd)}"
mkdir -p "$LOG_DIR"

login() {
  local email="$1"
  curl -fsS -X POST "$BASE/api/auth/login" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"password\":\"Demo123!\"}"
}

ADMIN="$(login admin@batchdemo.dev)"
ANALYST="$(login analyst@batchdemo.dev)"
REVIEWER="$(login reviewer@batchdemo.dev)"
printf '%s\n' "$ADMIN" "$ANALYST" "$REVIEWER" > "$LOG_DIR/logins.jsonl"
ANALYST_TOKEN="$(printf '%s' "$ANALYST" | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')"
REVIEWER_TOKEN="$(printf '%s' "$REVIEWER" | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')"

DATASETS="$(curl -fsS "$BASE/api/datasets" -H "Authorization: Bearer $ANALYST_TOKEN")"
printf '%s' "$DATASETS" > "$LOG_DIR/datasets.json"
ANALYSES="$(curl -fsS "$BASE/api/analyses" -H "Authorization: Bearer $ANALYST_TOKEN")"
printf '%s' "$ANALYSES" > "$LOG_DIR/analyses-before.json"
ANALYSIS_ID="$(printf '%s' "$ANALYSES" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["items"][0]["id"])')"

curl -fsS -X POST "$BASE/api/analyses/$ANALYSIS_ID/run" \
  -H "Authorization: Bearer $ANALYST_TOKEN" \
  -H 'Content-Type: application/json' > "$LOG_DIR/run-main.json"

DATASET_ID="$(printf '%s' "$DATASETS" | python3 -c 'import json,sys;print(json.load(sys.stdin)["items"][0]["id"])')"
REVIEWER_STATUS="$(curl -sS -o "$LOG_DIR/reviewer-forbidden.json" -w '%{http_code}' \
  -X POST "$BASE/api/analyses" -H "Authorization: Bearer $REVIEWER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"复核员不应创建\",\"dataset_id\":\"$DATASET_ID\"}")"
if [ "$REVIEWER_STATUS" != "403" ]; then
  echo "reviewer permission expected 403, got $REVIEWER_STATUS" >&2
  exit 1
fi

curl -fsS "$BASE/api/audit" -H "Authorization: Bearer $ANALYST_TOKEN" > "$LOG_DIR/audit.json"
echo "smoke passed: three logins, analyst run, reviewer 403, audit readable"
