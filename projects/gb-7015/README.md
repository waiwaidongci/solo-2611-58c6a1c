# 交易异常复核台

弦月支付（夜间风控组）的数据分析工作台。夜间风控需要在低人工值守下筛出异常交易，同时保证复核员能理解命中原因。

## 真实场景

- 当前工作流：规则引擎按固定金额阈值告警，复核员逐条查看商户和历史流水。
- 痛点：固定阈值难适应夜间波动；告警缺少可解释信号；重复告警占用复核时间。
- 上游：业务导出、实验室复核或历史归档数据。
- 本系统：统一资产登记、分析编排、Python 计算、结果复核与审计。
- 下游：业务负责人、数据管理员与复核员在周会/评审中使用结果。

## 功能

- 夜间告警：核心指标、数据状态与近期运行。
- 交易资产：资产列表、样本量与校验摘要。
- 检测编排：从资产创建分析方案并触发运行。
- 异常复核：查看真实 Python 计算结果、方法、限制与表格。
- 治理审计：审计日志、复核意见与角色权限追踪。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec backend python -m scripts.seed_demo
```

访问：

- 前端：http://localhost:18214
- 后端接口：http://localhost:19214/api/health
- 数据库映射：localhost:17714

## 演示账号

| 角色 | 邮箱 | 密码 | 权限 |
|---|---|---|---|
| 数据管理员 | admin@batchdemo.dev | Demo123! | 全部页面、创建与运行 |
| 分析员 | analyst@batchdemo.dev | Demo123! | 创建资产、方案与运行 |
| 业务复核员 | reviewer@batchdemo.dev | Demo123! | 只读结果、提交复核意见 |

## 技术栈

| 服务 | 技术 |
|---|---|
| frontend | react + TypeScript + Vite + Nginx |
| backend | Python 3.11 + FastAPI + SQLAlchemy |
| worker | Celery + Redis |
| db | postgres |
| redis | Redis 7 |

## 枚举位置

- 后端：`backend/src/constants/enums.py`
- 后端业务标签：`backend/src/constants/domain.py`
- 前端：`frontend/src/constants/enums.ts`
- 前端业务标签：`frontend/src/constants/domain.ts`

## 目录

```text
frontend/       # 页面、组件、store、API
backend/        # routes/controllers/services/models/schemas/middlewares
test-artifacts/ # 由批次 QA 放在项目目录之外
```

## 环境变量

见 `.env.example`。`.env` 不提交。接口统一由 Nginx `/api/` 代理。

## 算法口径

Isolation Forest 无监督异常分：后端按输入样本真实计算并返回效应、区间或评分。

稳健 z-score 信号解释：作为第二层诊断；结果、方法和限制同时返回，前端不硬编码图形数据。

## License

MIT
