# 设备特征试验室

拓野智能装备（预测性维护团队）的数据分析工作台。维修团队从振动、温度和电流信号提取了大量候选特征，需要筛掉噪声并保留可部署的少量指标。

## 真实场景

- 当前工作流：算法工程师在笔记本里逐版跑特征重要性，结果散落在多个 notebook。
- 痛点：高相关特征重复占位；缺失率与稳定性未纳入门槛；筛选版本无法复现。
- 上游：业务导出、实验室复核或历史归档数据。
- 本系统：统一资产登记、分析编排、Python 计算、结果复核与审计。
- 下游：业务负责人、数据管理员与复核员在周会/评审中使用结果。

## 功能

- 特征库存：核心指标、数据状态与近期运行。
- 设备资产：资产列表、样本量与校验摘要。
- 筛选编排：从资产创建分析方案并触发运行。
- 候选对比：查看真实 Python 计算结果、方法、限制与表格。
- 治理审计：审计日志、复核意见与角色权限追踪。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec backend python -m scripts.seed_demo
```

访问：

- 前端：http://localhost:18207
- 后端接口：http://localhost:19207/api/health
- 数据库映射：localhost:17707

## 演示账号

| 角色 | 邮箱 | 密码 | 权限 |
|---|---|---|---|
| 数据管理员 | admin@batchdemo.dev | Demo123! | 全部页面、创建与运行 |
| 分析员 | analyst@batchdemo.dev | Demo123! | 创建资产、方案与运行 |
| 业务复核员 | reviewer@batchdemo.dev | Demo123! | 只读结果、提交复核意见 |

## 技术栈

| 服务 | 技术 |
|---|---|
| frontend | vue + TypeScript + Vite + Nginx |
| backend | Python 3.11 + FastAPI + SQLAlchemy |
| worker | Celery + Redis |
| db | mysql |
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

互信息分类评分：后端按输入样本真实计算并返回效应、区间或评分。

方差阈值与相关性去冗余：作为第二层诊断；结果、方法和限制同时返回，前端不硬编码图形数据。

## License

MIT
