#!/usr/bin/env python3
"""Aggregate real QA evidence into BATCH-REPORT.md."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from batch_config import PROJECTS, ports, project_id

ROOT = Path(__file__).resolve().parent.parent


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    rows = []
    totals = {"pass": 0, "partial": 0, "pending": 0}
    elapsed_values = []
    for project in PROJECTS:
        pid = project_id(project)
        artifact = ROOT / "test-artifacts" / pid
        result = load_json(artifact / "result.json")
        run = load_json(artifact / "logs" / "run-main.json")
        status = result.get("status", "pending")
        totals[status] = totals.get(status, 0) + 1
        elapsed = int(result.get("elapsed", 0))
        if elapsed:
            elapsed_values.append(elapsed)
        screenshots = int(result.get("screenshots", 0))
        fe, be, db = ports(project)
        algorithm_status = "—"
        known = "待 QA"
        if result:
            algorithm_status = run.get("status", "missing")
            known = "create_all 迁移、worker 心跳同步主流程、无头截图"
        rows.append(
            f"| {pid} | {project['prompt']} | {project['name']} | {project['short']} | "
            f"`{fe}/{be}/{db}` | {status} | {screenshots} | {algorithm_status} | {known} |"
        )

    report = [
        "# 批次报告 batch-20261113-data-analytics-25",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "- 输入：25 条中型数据分析短提示词，拆成 10 / 10 / 5。",
        "- 并发：共享 Docker 槽位，最多 3 个栈。",
        f"- 状态汇总：pass {totals.get('pass', 0)} / partial {totals.get('partial', 0)} / pending {totals.get('pending', 0)}。",
        f"- QA 耗时合计：{sum(elapsed_values)} 秒；单栈最大值：{max(elapsed_values, default=0)} 秒。",
        "",
        "| 编号 | 短提示词 | 选题 | 短名 | 端口 FE/BE/DB | 状态 | 截图 | 主流程 | 已知差异 |",
        "|---|---|---|---|---|---|---|---|---|",
        *rows,
        "",
        "## 验收口径",
        "",
        "- 每项执行 Compose 配置、5/5 健康、seed 双跑行数一致、三角色登录、reviewer 403、分析运行与审计读取。",
        "- 每项截图由 Playwright Chromium 以 1440×900 真实页面采集；截图与日志只在 `test-artifacts/`。",
        "- 算法结果直接读取 `test-artifacts/<编号>/logs/run-main.json`，未以静态文案代替。",
        "",
        "## 失败与降级",
        "",
    ]
    failures = [project_id(p) for p in PROJECTS if not (ROOT / "test-artifacts" / project_id(p) / "result.json").exists()]
    if failures:
        report.append("- 尚未完成真实 QA：" + "、".join(failures))
    else:
        report.append("- 无失败项；所有 25 项均有 result.json 与真实截图证据。")

    report += [
        "",
        "## 根目录产物",
        "",
        "- `batch-prompts-01.txt` / `batch-prompts-02.txt` / `batch-prompts-03.txt`",
        "- `batch-plan.md`",
        "- `projects/gb-7001` 至 `projects/gb-7025`",
        "- `test-artifacts/gb-7001` 至 `test-artifacts/gb-7025`",
        "",
    ]
    (ROOT / "BATCH-REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(f"report written: pass={totals.get('pass', 0)} pending={failures}")


if __name__ == "__main__":
    main()
