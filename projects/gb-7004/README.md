# 检验分布漂移台

澄明医学检验所（9 个实验室）的数据分析工作台。生化指标每月受试剂批号和质控品更换影响，质量负责人需要判断结果分布是否发生实质漂移。

## 真实场景

- 当前工作流：质控员导出月度结果，比较均值与直方图，异常时召集实验室负责人复盘。
- 痛点：只看均值漏掉方差变化；不同项目量纲难以横向比较；处置阈值写死在文档里。
- 上游：业务导出、实验室复核或历史归档数据。
- 本系统：统一资产登记、分析编排、Python 计算、结果复核与审计。
- 下游：业务负责人、数据管理员与复核员在周会/评审中使用结果。

## 功能

- 漂移雷达：核心指标、数据状态与近期运行。
- 质控资产：资产列表、样本量与校验摘要。
- 监测编排：从资产创建分析方案并触发运行。
- 分布对比结果：查看真实 Python 计算结果、方法、限制与表格。
- 治理审计：审计日志、复核意见与角色权限追踪。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec backend python -m scripts.seed_demo
```

访问：

- 前端：http://localhost:18203
- 后端接口：http://localhost:19203/api/health
- 数据库映射：localhost:17703

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

Kolmogorov-Smirnov 分布检验：后端按输入样本真实计算并返回效应、区间或评分。

Population Stability Index 分箱漂移：作为第二层诊断；结果、方法和限制同时返回，前端不硬编码图形数据。

## License

MIT
