# gb-7019 测试记录

- 执行日期：2026-11-13 01:21:43 CST
- 端口：前端 18218 / 后端 19218
- Docker：Docker version 29.4.0, build 9d7ad9f
- 浏览器：Playwright Chromium，1440×900
- 槽位：3（全局 SLOTS=3）

## 真实结果

| 检查 | 结果 | 证据 |
|---|---|---|
| `docker compose config --quiet` | 通过 | logs/compose-config.log |
| 5 服务健康 | 5/5 healthy | logs/compose-status.log |
| seed 连续两次幂等 | 通过，行数完全一致 | logs/seed-counts.jsonl |
| 三账号登录与权限差异 | 通过，reviewer 创建返回 403 | logs/logins.jsonl、reviewer-forbidden.json |
| 主流程创建 → 执行 → 结果 | 通过 | run-main.json |
| 真实截图 | 6 张 | screenshots/ |
| 浏览器控制台错误 | 见 screenshots.out / console-errors.json | 真实采集 |

## 行数快照

```json
{"analyses": 4, "analysis_runs": 3, "datasets": 3, "users": 3}
```

## 耗时

- QA 总耗时：42s（不含已存在的构建缓存）

## 已知差异

- 本地 QA 使用浏览器无头模式；Google Fonts 需联网，离线时回退到声明字体族。
- 当前数据库初始化使用 `create_all`，生产演进应接入 Alembic。
- worker 以 Redis 心跳任务证明健康，主流程同步在 backend 执行，避免异步轮询影响首次验收。
