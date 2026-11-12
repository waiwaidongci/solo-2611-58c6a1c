# 田间试验判读册

青穗农业试验站（31 个示范田块）的数据分析工作台。育种站并行比较肥料与播期组合，每季有大量小样本试验，需要统一判读并控制假发现。

## 真实场景

- 当前工作流：记录员用纸质表格收产，统计员逐个复制到软件做 t 检验，异常值靠经验剔除。
- 痛点：批量检验容易误报；品种间样本量差异大；判读依据无法追溯。
- 上游：业务导出、实验室复核或历史归档数据。
- 本系统：统一资产登记、分析编排、Python 计算、结果复核与审计。
- 下游：业务负责人、数据管理员与复核员在周会/评审中使用结果。

## 功能

- 季试验总览：核心指标、数据状态与近期运行。
- 田块资产：资产列表、样本量与校验摘要。
- 批量比较编排：从资产创建分析方案并触发运行。
- 检验判读册：查看真实 Python 计算结果、方法、限制与表格。
- 治理审计：审计日志、复核意见与角色权限追踪。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec backend python -m scripts.seed_demo
```

访问：

- 前端：http://localhost:18202
- 后端接口：http://localhost:19202/api/health
- 数据库映射：localhost:17702

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

Welch t 检验：后端按输入样本真实计算并返回效应、区间或评分。

Benjamini-Hochberg FDR 校正：作为第二层诊断；结果、方法和限制同时返回，前端不硬编码图形数据。

## License

MIT
