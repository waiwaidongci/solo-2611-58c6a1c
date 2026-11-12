#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 1 ]; then echo "usage: qa_project.sh gb-7001" >&2; exit 2; fi
ID="$1"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="$ROOT/projects/$ID"
ART="$ROOT/test-artifacts/$ID"
SLOT_SCRIPT="/Users/ali/.codex/skills/pr-batch-project/scripts/slot.sh"
mkdir -p "$ART/logs" "$ART/screenshots"
find "$ART/screenshots" -maxdepth 1 -type f -name '*.png' -delete
export SLOTS=3
SLOT="$(bash "$SLOT_SCRIPT" acquire)"
cleanup() {
  (cd "$PROJECT" && docker compose down -v --remove-orphans) > "$ART/logs/compose-down.log" 2>&1 || true
  bash "$SLOT_SCRIPT" release "$SLOT" >/dev/null 2>&1 || true
}
trap cleanup EXIT

START="$(date +%s)"
printf 'slot=%s\n' "$SLOT" | tee "$ART/logs/slot.txt"
(cd "$PROJECT" && docker compose config --quiet) > "$ART/logs/compose-config.log" 2>&1
(cd "$PROJECT" && docker compose up -d --build) > "$ART/logs/compose-up.log" 2>&1

for i in $(seq 1 90); do
  IDS="$(cd "$PROJECT" && docker compose ps -q)"
  COUNT="$(printf '%s\n' "$IDS" | sed '/^$/d' | wc -l | tr -d ' ')"
  HEALTHY=0
  for cid in $IDS; do
    STATE="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || true)"
    [ "$STATE" = "healthy" ] && HEALTHY=$((HEALTHY + 1))
  done
  [ "$COUNT" = "5" ] && [ "$HEALTHY" = "5" ] && break
  sleep 4
  if [ "$i" = "90" ]; then
    (cd "$PROJECT" && docker compose ps) > "$ART/logs/compose-status-failed.log" 2>&1 || true
    (cd "$PROJECT" && docker compose logs --tail=200) > "$ART/logs/compose-logs-failed.log" 2>&1 || true
    echo "health timeout: count=$COUNT healthy=$HEALTHY" >&2
    exit 1
  fi
done
(cd "$PROJECT" && docker compose ps) > "$ART/logs/compose-status.log" 2>&1

COUNT_SQL='import json;from sqlalchemy import func,select;from src.database import SessionLocal;from src.models.user import User;from src.models.dataset import Dataset;from src.models.analysis import Analysis;from src.models.analysis_run import AnalysisRun;db=SessionLocal();print(json.dumps({m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in (User,Dataset,Analysis,AnalysisRun)},sort_keys=True))'
ONE="$(cd "$PROJECT" && docker compose exec -T backend python -c "$COUNT_SQL")"
(cd "$PROJECT" && docker compose exec -T backend python -m scripts.seed_demo) > "$ART/logs/seed-second.log" 2>&1
TWO="$(cd "$PROJECT" && docker compose exec -T backend python -c "$COUNT_SQL")"
printf '%s\n%s\n' "$ONE" "$TWO" > "$ART/logs/seed-counts.jsonl"
[ "$ONE" = "$TWO" ] || { echo "seed not idempotent: $ONE != $TWO" >&2; exit 1; }

BACKEND_PORT="$(grep '^BACKEND_PORT=' "$PROJECT/.env" | cut -d= -f2)"
FRONTEND_PORT="$(grep '^FRONTEND_PORT=' "$PROJECT/.env" | cut -d= -f2)"
BACKEND_URL="http://localhost:$BACKEND_PORT" LOG_DIR="$ART/logs" bash "$ART/tests/smoke.sh" | tee "$ART/logs/smoke.out"
BASE_URL="http://localhost:$FRONTEND_PORT" SCREENSHOT_DIR="$ART/screenshots" node "$ART/tests/screenshots.cjs" | tee "$ART/logs/screenshots.out"

SHOT_COUNT="$(find "$ART/screenshots" -name '*.png' -type f | wc -l | tr -d ' ')"
[ "$SHOT_COUNT" -ge 4 ] || { echo "expected >=4 screenshots, got $SHOT_COUNT" >&2; exit 1; }
END="$(date +%s)"
ELAPSED="$((END - START))"

cat > "$ART/TESTING.md" <<EOF
# $ID 测试记录

- 执行日期：$(date '+%Y-%m-%d %H:%M:%S %Z')
- 端口：前端 $FRONTEND_PORT / 后端 $BACKEND_PORT
- Docker：$(docker --version)
- 浏览器：Playwright Chromium，1440×900
- 槽位：${SLOT}（全局 SLOTS=3）

## 真实结果

| 检查 | 结果 | 证据 |
|---|---|---|
| \`docker compose config --quiet\` | 通过 | logs/compose-config.log |
| 5 服务健康 | 5/5 healthy | logs/compose-status.log |
| seed 连续两次幂等 | 通过，行数完全一致 | logs/seed-counts.jsonl |
| 三账号登录与权限差异 | 通过，reviewer 创建返回 403 | logs/logins.jsonl、reviewer-forbidden.json |
| 主流程创建 → 执行 → 结果 | 通过 | run-main.json |
| 真实截图 | $SHOT_COUNT 张 | screenshots/ |
| 浏览器控制台错误 | 见 screenshots.out / console-errors.json | 真实采集 |

## 行数快照

\`\`\`json
$ONE
\`\`\`

## 耗时

- QA 总耗时：${ELAPSED}s（不含已存在的构建缓存）

## 已知差异

- 本地 QA 使用浏览器无头模式；Google Fonts 需联网，离线时回退到声明字体族。
- 当前数据库初始化使用 \`create_all\`，生产演进应接入 Alembic。
- worker 以 Redis 心跳任务证明健康，主流程同步在 backend 执行，避免异步轮询影响首次验收。
EOF

printf '{"id":"%s","status":"pass","screenshots":%s,"elapsed":%s,"ports":[%s,%s]}\n' \
  "$ID" "$SHOT_COUNT" "$ELAPSED" "$FRONTEND_PORT" "$BACKEND_PORT" > "$ART/result.json"
echo "QA PASS $ID screenshots=$SHOT_COUNT elapsed=${ELAPSED}s"
