#!/usr/bin/env python3
"""Generate the 25 self-contained analytics projects and their test harnesses."""

from __future__ import annotations

import json
import shutil
import textwrap
from pathlib import Path

from batch_config import PROJECTS, ports, project_id, validate_config

ROOT = Path(__file__).resolve().parent.parent


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def q(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def generate_prompt_files() -> None:
    for batch_index, start in enumerate((0, 10, 20), 1):
        projects = PROJECTS[start : start + 10]
        lines = [project["prompt"] for project in projects]
        write(ROOT / f"batch-prompts-{batch_index:02d}.txt", "\n".join(lines) + "\n")


def generate_plan() -> None:
    lines = [
        "# 25 项数据分析与数据应用批量计划",
        "",
        "- 日期：2026-11-13",
        "- 总量：25 个中型项目，拆分为 10 / 10 / 5 三个子批。",
        "- 并发：全批次共享 Docker 槽位，最多 3 个栈同时运行。",
        "- 端口：全局连续分配，避免三个子批并行时冲突。",
        "- 前端：React 18 与 Vue 3 交替；数据库：PostgreSQL 16 与 MySQL 8.0 交替。",
        "- 统一硬约束：5 服务、FastAPI、JWT 三角色、seed 幂等、2 个 Python 真算法、5 个业务页面、4 张真实截图。",
        "",
        "## 总表",
        "",
        "| 编号 | 子批 | 短提示词 | 选题 | 短名 | 前端/数据库 | 端口 FE/BE/DB |",
        "|---|---|---|---|---|---|---|",
    ]
    for project in PROJECTS:
        fe, be, db = ports(project)
        batch = (project["n"] - 1) // 10 + 1
        lines.append(
            f"| {project_id(project)} | {batch} | {project['prompt']} | "
            f"{project['name']} | `{project['short']}` | "
            f"{project['frontend']} / {project['db']} | `{fe}/{be}/{db}` |"
        )

    lines += ["", "## 内部 Brief", ""]
    for project in PROJECTS:
        fe, be, db = ports(project)
        pains = "；".join(project["pains"])
        lines += [
            f"### {project_id(project)} {project['name']}",
            "",
            f"- 模拟客户：{project['client']}",
            f"- 当前工作流：{project['workflow']}",
            f"- 核心痛点：{pains}",
            f"- 核心实体：{' / '.join(project['entities'])}",
            f"- 核心页面：{' / '.join(project['pages'])}",
            f"- Python 算法：{'；'.join(project['algorithms'])}",
            f"- UI 方向：{project['visual']}；字体 {project['fonts'][0]} + {project['fonts'][1]}",
            f"- seed：3 个角色、3 个数据资产、4 个分析方案、3 个运行结果、审计与复核记录，自然键幂等。",
            f"- 验收：登录 → 选择资产 → 新建运行 → Python 计算 → 查看结果 → 审计可追溯；端口 `{fe}/{be}/{db}`。",
            "",
        ]
    write(ROOT / "batch-plan.md", "\n".join(lines))


def compose_file(project: dict) -> str:
    fe, be, db_port = ports(project)
    short = project["short"]
    if project["db"] == "postgres":
        db_image = "postgres:16-alpine"
        db_env = """
      POSTGRES_DB: ${POSTGRES_DB:-analytics}
      POSTGRES_USER: ${POSTGRES_USER:-batch}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-batchpass}
"""
        db_health = (
            'test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-batch} '
            '-d ${POSTGRES_DB:-analytics}"]'
        )
        db_mount = "/var/lib/postgresql/data"
        default_db_url = "postgresql+psycopg2://batch:batchpass@db:5432/analytics"
    else:
        db_image = "mysql:8.0"
        db_env = """
      MYSQL_DATABASE: ${MYSQL_DATABASE:-analytics}
      MYSQL_USER: ${MYSQL_USER:-batch}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-batchpass}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-rootpass}
"""
        db_health = (
            'test: ["CMD-SHELL", "mysqladmin ping -h localhost -u root '
            '-p$$MYSQL_ROOT_PASSWORD --silent"]'
        )
        db_mount = "/var/lib/mysql"
        default_db_url = "mysql+pymysql://batch:batchpass@db:3306/analytics"
    return f"""
name: {short}

services:
  frontend:
    build:
      context: ./frontend
    container_name: ${{COMPOSE_PROJECT_NAME:-{short}}}-frontend
    ports:
      - "${{FRONTEND_PORT:-{fe}}}:80"
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://127.0.0.1/healthz | grep ok"]
      interval: 10s
      timeout: 3s
      retries: 10

  backend:
    build:
      context: ./backend
    container_name: ${{COMPOSE_PROJECT_NAME:-{short}}}-backend
    environment:
      DATABASE_URL: ${{DATABASE_URL:-{default_db_url}}}
      REDIS_URL: ${{REDIS_URL:-redis://redis:6379/0}}
      JWT_SECRET: ${{JWT_SECRET:-change-this-in-local}}
      SEED_DEMO: "true"
      PROJECT_KEY: {q(project["algorithm"])}
    ports:
      - "${{BACKEND_PORT:-{be}}}:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - artifacts:/app/artifacts
    command: >
      sh -c "python -m scripts.seed_demo --wait &&
             uvicorn src.main:app --host 0.0.0.0 --port 8000"
    healthcheck:
      test: ["CMD-SHELL", "python -c \\"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')\\""]
      interval: 10s
      timeout: 5s
      retries: 18

  worker:
    build:
      context: ./backend
    container_name: ${{COMPOSE_PROJECT_NAME:-{short}}}-worker
    environment:
      DATABASE_URL: ${{DATABASE_URL:-{default_db_url}}}
      REDIS_URL: ${{REDIS_URL:-redis://redis:6379/0}}
      JWT_SECRET: ${{JWT_SECRET:-change-this-in-local}}
      PROJECT_KEY: {q(project["algorithm"])}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - artifacts:/app/artifacts
    command: celery -A src.worker.celery_app worker --loglevel=INFO --concurrency=1
    healthcheck:
      test: ["CMD-SHELL", "celery -A src.worker.celery_app inspect ping -d celery@$$HOSTNAME | grep -q pong"]
      interval: 20s
      timeout: 10s
      retries: 10

  db:
    image: {db_image}
    container_name: ${{COMPOSE_PROJECT_NAME:-{short}}}-db
    environment:{db_env.rstrip()}
    ports:
      - "${{DB_PORT:-{db_port}}}:{'5432' if project['db'] == 'postgres' else '3306'}"
    volumes:
      - dbdata:{db_mount}
    healthcheck:
      {db_health}
      interval: 10s
      timeout: 5s
      retries: 20

  redis:
    image: redis:7-alpine
    container_name: ${{COMPOSE_PROJECT_NAME:-{short}}}-redis
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 12

volumes:
  dbdata:
    name: ${{COMPOSE_PROJECT_NAME:-{short}}}-dbdata
  redisdata:
    name: ${{COMPOSE_PROJECT_NAME:-{short}}}-redisdata
  artifacts:
    name: ${{COMPOSE_PROJECT_NAME:-{short}}}-artifacts
"""


def env_files(project: dict) -> tuple[str, str]:
    fe, be, db_port = ports(project)
    short = project["short"]
    if project["db"] == "postgres":
        db_env = """POSTGRES_DB=analytics
POSTGRES_USER=batch
POSTGRES_PASSWORD=batchpass
DATABASE_URL=postgresql+psycopg2://batch:batchpass@db:5432/analytics"""
    else:
        db_env = """MYSQL_DATABASE=analytics
MYSQL_USER=batch
MYSQL_PASSWORD=batchpass
MYSQL_ROOT_PASSWORD=rootpass
DATABASE_URL=mysql+pymysql://batch:batchpass@db:3306/analytics"""
    content = f"""COMPOSE_PROJECT_NAME={short}
FRONTEND_PORT={fe}
BACKEND_PORT={be}
DB_PORT={db_port}
{db_env}
REDIS_URL=redis://redis:6379/0
JWT_SECRET={short}-local-secret
SEED_DEMO=true
"""
    return content, content


def backend_files(project: dict) -> dict[str, str]:
    short = project["short"]
    entities = project["entities"]
    algorithm = project["algorithm"]
    labels_json = json.dumps(entities, ensure_ascii=False, indent=2)
    algorithm_labels = json.dumps(project["algorithms"], ensure_ascii=False, indent=2)
    files: dict[str, str] = {}
    files["requirements.txt"] = """
fastapi==0.115.6
uvicorn[standard]==0.34.0
SQLAlchemy==2.0.36
psycopg2-binary==2.9.10
PyMySQL==1.1.1
cryptography==44.0.0
redis==6.4.0
celery==5.4.0
python-jose[cryptography]==3.3.0
pydantic-settings==2.7.1
email-validator==2.2.0
numpy==2.2.1
scipy==1.15.0
scikit-learn==1.6.0
"""
    files["Dockerfile"] = """
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
    files["src/__init__.py"] = ""
    files["src/config.py"] = f"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./local.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "{short}-local-secret"
    jwt_algorithm: str = "HS256"
    access_expiry_minutes: int = 720
    project_key: str = "{algorithm}"
    seed_demo: bool = True

    model_config = {{"env_file": ".env", "extra": "ignore"}}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
"""
    files["src/database.py"] = """
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""
    files["src/constants/enums.py"] = """
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    REVIEWER = "reviewer"


class EntityStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisKind(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
"""
    files["src/constants/domain.py"] = f"""
PROJECT_KEY = {q(algorithm)}
PROJECT_NAME = {q(project["name"])}
ENTITY_LABELS = {labels_json}
ALGORITHM_LABELS = {algorithm_labels}
ROLE_LABELS = {{
    "admin": "数据管理员",
    "analyst": "分析员",
    "reviewer": "业务复核员",
}}
"""
    files["src/models/__init__.py"] = """
from src.models.analysis import Analysis
from src.models.analysis_run import AnalysisRun
from src.models.audit_log import AuditLog
from src.models.comment import Comment
from src.models.dataset import Dataset
from src.models.user import User
from src.models.workspace import Workspace

__all__ = [
    "Analysis", "AnalysisRun", "AuditLog", "Comment", "Dataset", "User", "Workspace"
]
"""
    files["src/models/common.py"] = """
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


def uuid4_str() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class IdMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
"""
    files["src/models/user.py"] = """
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.common import IdMixin, TimestampMixin


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(24), index=True)
    password_hash: Mapped[str] = mapped_column(String(240))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
"""
    files["src/models/workspace.py"] = """
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.common import IdMixin, TimestampMixin


class Workspace(IdMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"
    natural_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    client_name: Mapped[str] = mapped_column(String(180))
    context_note: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
"""
    files["src/models/dataset.py"] = """
from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.common import IdMixin, TimestampMixin


class Dataset(IdMixin, TimestampMixin, Base):
    __tablename__ = "datasets"
    natural_key: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    source: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(24), default="ready")
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    rows: Mapped[list] = mapped_column(JSON, default=list)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True)
    created_by: Mapped[str] = mapped_column(String(36), index=True)
"""
    files["src/models/analysis.py"] = """
from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.common import IdMixin, TimestampMixin


class Analysis(IdMixin, TimestampMixin, Base):
    __tablename__ = "analyses"
    natural_key: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    kind: Mapped[str] = mapped_column(String(24), default="primary")
    status: Mapped[str] = mapped_column(String(24), default="ready")
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    dataset_id: Mapped[str] = mapped_column(String(36), index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True)
    created_by: Mapped[str] = mapped_column(String(36), index=True)
"""
    files["src/models/analysis_run.py"] = """
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.common import IdMixin, TimestampMixin


class AnalysisRun(IdMixin, TimestampMixin, Base):
    __tablename__ = "analysis_runs"
    natural_key: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="draft")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[list] = mapped_column(JSON, default=list)
    error_message: Mapped[str] = mapped_column(Text, default="")
    checksum: Mapped[str] = mapped_column(String(64), default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_id: Mapped[str] = mapped_column(String(36), index=True)
    created_by: Mapped[str] = mapped_column(String(36), index=True)
"""
    files["src/models/audit_log.py"] = """
from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.common import IdMixin, TimestampMixin


class AuditLog(IdMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource_type: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str] = mapped_column(String(80))
    actor_id: Mapped[str] = mapped_column(String(36), index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
"""
    files["src/models/comment.py"] = """
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.common import IdMixin, TimestampMixin


class Comment(IdMixin, TimestampMixin, Base):
    __tablename__ = "comments"
    natural_key: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    body: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(24), default="pending")
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    author_id: Mapped[str] = mapped_column(String(36), index=True)
"""

    # Schemas
    files["src/schemas/common.py"] = """
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message: str


class Timestamped(ORMModel):
    created_at: datetime
    updated_at: datetime
"""
    files["src/schemas/auth.py"] = """
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
"""
    files["src/schemas/workspace.py"] = """
from src.schemas.common import ORMModel, Timestamped


class WorkspaceRead(Timestamped):
    id: str
    name: str
    client_name: str
    context_note: str
    owner_id: str
"""
    files["src/schemas/dataset.py"] = """
from pydantic import BaseModel
from src.schemas.common import ORMModel, Timestamped


class DatasetRead(Timestamped):
    id: str
    name: str
    source: str
    status: str
    row_count: int
    checksum: str
    description: str
    workspace_id: str
    created_by: str


class DatasetCreate(BaseModel):
    name: str
    source: str = "manual"
    description: str = ""
    rows: list[dict] = []


class DatasetList(ORMModel):
    items: list[DatasetRead]
    total: int
"""
    files["src/schemas/analysis.py"] = """
from pydantic import BaseModel
from src.schemas.common import ORMModel, Timestamped


class AnalysisRead(Timestamped):
    id: str
    name: str
    kind: str
    status: str
    hypothesis: str
    config: dict
    dataset_id: str
    workspace_id: str
    created_by: str


class AnalysisCreate(BaseModel):
    name: str
    dataset_id: str
    kind: str = "primary"
    hypothesis: str = ""
    config: dict = {}


class AnalysisList(ORMModel):
    items: list[AnalysisRead]
    total: int
"""
    files["src/schemas/analysis_run.py"] = """
from datetime import datetime
from pydantic import BaseModel
from src.schemas.common import ORMModel


class RunRead(ORMModel):
    id: str
    status: str
    result: dict
    metrics: list
    error_message: str
    checksum: str
    started_at: datetime | None
    completed_at: datetime | None
    analysis_id: str
    created_by: str
    created_at: datetime


class RunList(ORMModel):
    items: list[RunRead]
    total: int


class CommentCreate(BaseModel):
    body: str
    decision: str = "pending"
"""
    files["src/schemas/audit_log.py"] = """
from src.schemas.common import ORMModel, Timestamped


class AuditRead(Timestamped):
    id: str
    action: str
    resource_type: str
    resource_id: str
    actor_id: str
    detail: dict


class AuditList(ORMModel):
    items: list[AuditRead]
    total: int
"""
    files["src/schemas/comment.py"] = """
from src.schemas.common import ORMModel, Timestamped


class CommentRead(Timestamped):
    id: str
    body: str
    decision: str
    run_id: str
    author_id: str
"""
    return files


ALGORITHM_SOURCES = {
    "ab_decision": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    grouped: dict[str, dict[str, float]] = {}
    for row in rows:
        group = str(row.get("group", "B"))
        bucket = grouped.setdefault(group, {"exposure": 0.0, "conversion": 0.0})
        bucket["exposure"] += float(row.get("exposure", row.get("users", 0)))
        bucket["conversion"] += float(row.get("conversion", row.get("converted", 0)))
    if len(grouped) < 2:
        raise ValueError("至少需要两个实验组")
    ordered = sorted(grouped.items(), key=lambda item: item[0])
    (control_name, control), (variant_name, variant) = ordered[:2]
    p1 = control["conversion"] / max(control["exposure"], 1)
    p2 = variant["conversion"] / max(variant["exposure"], 1)
    pooled = (control["conversion"] + variant["conversion"]) / max(
        control["exposure"] + variant["exposure"], 1
    )
    se = math.sqrt(max(pooled * (1 - pooled) * (1 / control["exposure"] + 1 / variant["exposure"]), 1e-12))
    z_value = (p2 - p1) / se
    p_value = math.erfc(abs(z_value) / math.sqrt(2))
    rng = np.random.default_rng(42)
    posterior = rng.beta(variant["conversion"] + 1, variant["exposure"] - variant["conversion"] + 1, 20000)
    prior = rng.beta(control["conversion"] + 1, control["exposure"] - control["conversion"] + 1, 20000)
    prob_better = float((posterior > prior).mean())
    lift = (p2 - p1) / max(p1, 1e-9)
    return _envelope(
        f"{variant_name} 比 {control_name} 的相对提升为 {lift:.1%}",
        f"两比例 z 检验 p={p_value:.4f}，后验胜率 {prob_better:.1%}。结论需结合实验预注册停止规则。",
        [
            _metric("相对提升", lift * 100, "%", "positive" if lift > 0 else "negative"),
            _metric("双侧 p 值", p_value, "", "positive" if p_value < 0.05 else "neutral"),
            _metric("后验胜率", prob_better * 100, "%", "positive" if prob_better > 0.9 else "neutral"),
            _metric("样本量", control["exposure"] + variant["exposure"], "人", "neutral"),
        ],
        [_series(control_name, p1 * 100), _series(variant_name, p2 * 100)],
        [
            {"label": name, "rate": round(value["conversion"] / max(value["exposure"], 1) * 100, 3),
             "exposure": int(value["exposure"]), "conversion": int(value["conversion"])}
            for name, value in ordered
        ],
        "two_proportion_z + beta_binomial",
        "观察性运行不能替代随机分流检查；连续偷看结果会抬高假阳性。",
    )
''',
    "correlation_diag": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    pairs: dict[str, list[tuple[float, float]]] = {}
    for row in rows:
        pair = str(row.get("pair", "温度-湿度"))
        try:
            pairs.setdefault(pair, []).append((float(row["x"]), float(row["y"])))
        except (KeyError, TypeError, ValueError):
            continue
    records = []
    for pair, values in pairs.items():
        if len(values) < 8:
            continue
        x = np.asarray([item[0] for item in values])
        y = np.asarray([item[1] for item in values])
        pearson = stats.pearsonr(x, y)
        spearman = stats.spearmanr(x, y)
        records.append({
            "pair": pair, "pearson": pearson.statistic, "spearman": spearman.statistic,
            "p_value": pearson.pvalue, "n": len(values)
        })
    if not records:
        raise ValueError("没有足够的相关分析数据")
    p_values = np.asarray([item["p_value"] for item in records])
    order = np.argsort(p_values)
    adjusted = np.empty_like(p_values)
    running = 1.0
    for rank in range(len(order) - 1, -1, -1):
        idx = order[rank]
        running = min(running, p_values[idx] * len(p_values) / (rank + 1))
        adjusted[idx] = running
    for record, q_value in zip(records, adjusted):
        record["q_value"] = float(q_value)
    records.sort(key=lambda item: abs(item["pearson"]), reverse=True)
    top = records[0]
    return _envelope(
        f"{top['pair']} 的相关最强，Pearson r={top['pearson']:.3f}",
        f"在 {len(records)} 组候选传感器对中完成 BH 校正，q={top['q_value']:.4f}。",
        [
            _metric("最强 Pearson", top["pearson"], "", "negative" if abs(top["pearson"]) > .8 else "neutral"),
            _metric("Spearman", top["spearman"], "", "neutral"),
            _metric("BH q 值", top["q_value"], "", "positive" if top["q_value"] < .05 else "neutral"),
            _metric("候选组合", len(records), "组", "neutral"),
        ],
        [_series(item["pair"], round(item["pearson"] * 100, 2)) for item in records[:8]],
        [
            {"label": item["pair"], "pearson": round(item["pearson"], 4),
             "spearman": round(item["spearman"], 4), "q": round(item["q_value"], 5), "n": item["n"]}
            for item in records
        ],
        "pearson_spearman + benjamini_hochberg",
        "相关不代表因果；传感器时钟偏移需在上游同步后才能做实时告警。",
    )
''',
    "hypothesis_batch": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    groups: dict[str, list[float]] = {}
    for row in rows:
        try:
            groups.setdefault(str(row.get("batch", "A")), []).append(float(row["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    names = sorted(groups)
    if len(names) < 2:
        raise ValueError("至少需要两个比较批次")
    control = groups[names[0]]
    records = []
    for name in names[1:]:
        test = stats.ttest_ind(groups[name], control, equal_var=False, nan_policy="omit")
        mean_diff = float(np.mean(groups[name]) - np.mean(control))
        records.append({"label": name, "diff": mean_diff, "p_value": float(test.pvalue)})
    p_values = np.asarray([item["p_value"] for item in records])
    order = np.argsort(p_values)
    running = 1.0
    q_values = np.empty_like(p_values)
    for rank in range(len(order) - 1, -1, -1):
        idx = order[rank]
        running = min(running, p_values[idx] * len(p_values) / (rank + 1))
        q_values[idx] = running
    for record, q_value in zip(records, q_values):
        record["q_value"] = float(q_value)
    records.sort(key=lambda item: abs(item["diff"]), reverse=True)
    top = records[0]
    return _envelope(
        f"{top['label']} 与 {names[0]} 的均值差最大：{top['diff']:+.3f}",
        f"Welch t 检验后使用 BH 控制批量假发现，最小 q={min(q_values):.4f}。",
        [
            _metric("最大均值差", top["diff"], "", "positive" if abs(top["diff"]) > 0 else "neutral"),
            _metric("最小 q 值", min(q_values), "", "positive" if min(q_values) < .05 else "neutral"),
            _metric("比较组数", len(records), "组", "neutral"),
            _metric("总样本", sum(len(values) for values in groups.values()), "份", "neutral"),
        ],
        [_series(item["label"], round(item["diff"], 4)) for item in records],
        [{"label": item["label"], "mean_diff": round(item["diff"], 4),
          "p_value": round(item["p_value"], 5), "q_value": round(item["q_value"], 5)} for item in records],
        "welch_t + bh_fdr",
        "小样本试验仍需检查异常值和田间空间效应；q 值不是效应大小。",
    )
''',
    "drift_monitor": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    periods: dict[str, list[float]] = {}
    for row in rows:
        try:
            periods.setdefault(str(row.get("period", "reference")), []).append(float(row["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    if "reference" not in periods or "current" not in periods:
        raise ValueError("需要 reference 与 current 两个分布")
    ref = np.asarray(periods["reference"])
    cur = np.asarray(periods["current"])
    ks = stats.ks_2samp(ref, cur)
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, 11)))
    ref_counts, _ = np.histogram(ref, bins=edges)
    cur_counts, _ = np.histogram(cur, bins=edges)
    ref_share = np.maximum(ref_counts / max(ref_counts.sum(), 1), 1e-6)
    cur_share = np.maximum(cur_counts / max(cur_counts.sum(), 1), 1e-6)
    psi = float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))
    return _envelope(
        f"KS 距离 {ks.statistic:.3f}，PSI {psi:.3f}",
        "PSI < 0.1 视为稳定，0.1-0.25 需复核，超过 0.25 需要处置。",
        [
            _metric("KS 距离", ks.statistic, "", "negative" if ks.statistic > .15 else "neutral"),
            _metric("KS p 值", ks.pvalue, "", "neutral"),
            _metric("PSI", psi, "", "negative" if psi > .25 else "positive" if psi < .1 else "neutral"),
            _metric("当前样本", len(cur), "份", "neutral"),
        ],
        [_series(f"分箱 {index + 1}", round((cur_share[index] - ref_share[index]) * 100, 3))
         for index in range(len(ref_share))],
        [{"label": f"分箱 {index + 1}", "reference": round(ref_share[index], 5),
          "current": round(cur_share[index], 5)} for index in range(len(ref_share))],
        "ks_2samp + population_stability_index",
        "漂移不等同于质量失控；试剂批号变更应先与质控规则联动解释。",
    )
''',
    "segment_kmeans": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    matrix = np.asarray([
        [float(row.get("recency", 0)), float(row.get("frequency", 0)), float(row.get("monetary", 0))]
        for row in rows
    ], dtype=float)
    if len(matrix) < 12:
        raise ValueError("会员样本不足")
    scaled = StandardScaler().fit_transform(matrix)
    k_value = int(config.get("clusters", 3))
    model = KMeans(n_clusters=k_value, random_state=42, n_init=10).fit(scaled)
    score = silhouette_score(scaled, model.labels_) if len(set(model.labels_)) > 1 else 0.0
    profiles = []
    for cluster in sorted(set(model.labels_)):
        subset = matrix[model.labels_ == cluster]
        profiles.append({
            "label": f"客群 {cluster + 1}",
            "size": int(len(subset)),
            "recency": round(float(subset[:, 0].mean()), 2),
            "frequency": round(float(subset[:, 1].mean()), 2),
            "monetary": round(float(subset[:, 2].mean()), 2),
        })
    profiles.sort(key=lambda item: item["monetary"], reverse=True)
    largest = max(profiles, key=lambda item: item["size"])
    return _envelope(
        f"形成 {k_value} 个客群，最大群 {largest['label']} 占 {largest['size'] / len(matrix):.1%}",
        f"K-means++ 轮廓系数 {score:.3f}；画像用于运营动作，不应替代人工抽检。",
        [
            _metric("轮廓系数", score, "", "positive" if score > .35 else "neutral"),
            _metric("客群数", k_value, "群", "neutral"),
            _metric("样本量", len(matrix), "人", "neutral"),
            _metric("最大群占比", largest["size"] / len(matrix) * 100, "%", "neutral"),
        ],
        [_series(item["label"], item["size"]) for item in profiles],
        profiles,
        "kmeans_plus_plus + silhouette",
        "簇编号没有天然业务顺序；上线前需用稳定性和运营可执行性复核。",
    )
''',
    "basket_rules": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    baskets = []
    for row in rows:
        items = row.get("items", [])
        if isinstance(items, list):
            baskets.append({str(item) for item in items if str(item).strip()})
    if len(baskets) < 20:
        raise ValueError("购物篮样本不足")
    min_support = float(config.get("min_support", 0.02))
    pair_counts: dict[tuple[str, str], int] = {}
    item_counts: dict[str, int] = {}
    for basket in baskets:
        for item in basket:
            item_counts[item] = item_counts.get(item, 0) + 1
        for left, right in itertools.combinations(sorted(basket), 2):
            pair_counts[(left, right)] = pair_counts.get((left, right), 0) + 1
    records = []
    for (left, right), count in pair_counts.items():
        support = count / len(baskets)
        if support < min_support:
            continue
        confidence = count / max(item_counts[left], 1)
        reverse_conf = count / max(item_counts[right], 1)
        lift = confidence / max(item_counts[right] / len(baskets), 1e-9)
        records.append({"left": left, "right": right, "support": support,
                        "confidence": confidence, "reverse_confidence": reverse_conf, "lift": lift})
    if not records:
        raise ValueError("当前支持度阈值下没有规则")
    records.sort(key=lambda item: item["lift"], reverse=True)
    top = records[0]
    return _envelope(
        f"{top['left']} → {top['right']} 的提升度最高：{top['lift']:.2f}",
        f"从 {len(baskets)} 个购物篮中保留 {len(records)} 条达到最小支持度的关联规则。",
        [
            _metric("最高 Lift", top["lift"], "", "positive"),
            _metric("支持度", top["support"] * 100, "%", "neutral"),
            _metric("置信度", top["confidence"] * 100, "%", "positive"),
            _metric("有效规则", len(records), "条", "neutral"),
        ],
        [_series(f"{item['left']}→{item['right']}", round(item["lift"], 3)) for item in records[:10]],
        [{"label": f"{item['left']} → {item['right']}", "support": round(item["support"], 4),
          "confidence": round(item["confidence"], 4), "lift": round(item["lift"], 4)}
         for item in records[:20]],
        "apriori_pairs + lift",
        "提升度只描述同篮共现，陈列动作仍要通过门店级对照实验验证。",
    )
''',
    "churn_model": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    matrix = np.asarray([[float(row.get(key, 0)) for key in ("tenure", "usage", "tickets", "login_gap")]
                         for row in rows], dtype=float)
    target = np.asarray([int(row.get("churned", 0)) for row in rows], dtype=int)
    if len(set(target.tolist())) < 2:
        raise ValueError("流失标签只有一个类别")
    model = LogisticRegression(max_iter=800, class_weight="balanced", random_state=42)
    model.fit(StandardScaler().fit_transform(matrix), target)
    probability = model.predict_proba(StandardScaler().fit(matrix).transform(matrix))[:, 1]
    auc_value = roc_auc_score(target, probability)
    rng = np.random.default_rng(42)
    boot = []
    for _ in range(120):
        idx = rng.integers(0, len(target), len(target))
        if len(set(target[idx].tolist())) < 2:
            continue
        boot.append(roc_auc_score(target[idx], probability[idx]))
    low, high = np.quantile(boot, [0.025, 0.975])
    feature_effect = sorted(
        [{"label": name, "value": float(coef)} for name, coef in
         zip(("在网月数", "周使用时长", "近90天工单", "登录间隔"), model.coef_[0])],
        key=lambda item: abs(item["value"]), reverse=True
    )
    risk_count = int((probability >= .6).sum())
    return _envelope(
        f"识别 {risk_count} 个高流失风险账户，AUC {auc_value:.3f}",
        f"Bootstrap 95% 区间 {low:.3f}-{high:.3f}；分数用于排序触达名单。",
        [
            _metric("ROC AUC", auc_value, "", "positive" if auc_value > .75 else "neutral"),
            _metric("95% 下限", low, "", "neutral"),
            _metric("高风险账户", risk_count, "户", "negative"),
            _metric("样本量", len(rows), "户", "neutral"),
        ],
        [_series(item["label"], round(item["value"], 3)) for item in feature_effect],
        [{"label": item["label"], "coefficient": round(item["value"], 4)} for item in feature_effect],
        "weighted_logistic + bootstrap_auc",
        "同一客户不得跨训练集和验证集；当前结果为演示集内评估。",
    )
''',
    "feature_select": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    keys = [key for key in rows[0] if key.startswith("f_")] if rows else []
    if not keys:
        raise ValueError("没有 f_ 开头的候选特征")
    matrix = np.asarray([[float(row.get(key, 0)) for key in keys] for row in rows], dtype=float)
    target = np.asarray([int(row.get("label", 0)) for row in rows], dtype=int)
    scores = mutual_info_classif(matrix, target, random_state=42)
    variances = matrix.var(axis=0)
    corr = np.abs(np.corrcoef(matrix, rowvar=False))
    kept, dropped = [], []
    for idx in np.argsort(scores)[::-1]:
        if variances[idx] <= 1e-9:
            dropped.append({"label": keys[idx], "reason": "零方差", "mi": 0.0})
            continue
        if any(corr[idx, other] > .85 for other in kept):
            dropped.append({"label": keys[idx], "reason": "高相关冗余", "mi": scores[idx]})
            continue
        kept.append(int(idx))
    records = [{"label": keys[idx], "mi": float(scores[idx]),
                "variance": float(variances[idx]), "kept": idx in kept} for idx in np.argsort(scores)[::-1]]
    return _envelope(
        f"保留 {len(kept)} / {len(keys)} 个候选特征",
        "先按互信息排序，再剔除零方差和 |r|>0.85 的冗余项。",
        [
            _metric("保留特征", len(kept), "个", "positive"),
            _metric("冗余剔除", sum(1 for item in dropped if item["reason"] == "高相关冗余"), "个", "neutral"),
            _metric("最高互信息", max(scores), "", "positive"),
            _metric("样本量", len(rows), "条", "neutral"),
        ],
        [_series(item["label"], item["mi"]) for item in records],
        [{"label": item["label"], "mutual_info": round(item["mi"], 5),
          "variance": round(item["variance"], 5), "kept": item["kept"]} for item in records],
        "mutual_information + variance_corr_gate",
        "特征筛选必须放在训练折内，当前全量演示分不能直接当作泛化能力。",
    )
''',
    "model_compare": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    target = np.asarray([int(row.get("y", 0)) for row in rows])
    model_keys = [key for key in ("p_base", "p_tree", "p_logit") if key in rows[0]]
    if len(model_keys) < 2:
        raise ValueError("至少需要两个候选模型的分数列")
    scores = {key: np.asarray([float(row.get(key, 0)) for row in rows]) for key in model_keys}
    aucs = {key: roc_auc_score(target, value) for key, value in scores.items()}
    ordered = sorted(aucs.items(), key=lambda item: item[1], reverse=True)
    rng = np.random.default_rng(42)
    diffs = []
    for _ in range(250):
        idx = rng.integers(0, len(target), len(target))
        if len(set(target[idx].tolist())) < 2:
            continue
        diffs.append(roc_auc_score(target[idx], scores[ordered[0][0]][idx]) -
                     roc_auc_score(target[idx], scores[ordered[1][0]][idx]))
    low, high = np.quantile(diffs, [.025, .975])
    names = {"p_base": "评分卡", "p_tree": "树模型", "p_logit": "逻辑模型"}
    return _envelope(
        f"{names.get(ordered[0][0], ordered[0][0])} 的 AUC 最高：{ordered[0][1]:.3f}",
        f"与第二名的成对差值 95% 区间为 [{low:+.3f}, {high:+.3f}]。",
        [
            _metric("最佳 AUC", ordered[0][1], "", "positive"),
            _metric("AUC 差值", ordered[0][1] - ordered[1][1], "", "neutral"),
            _metric("差值下限", low, "", "positive" if low > 0 else "neutral"),
            _metric("评测样本", len(target), "条", "neutral"),
        ],
        [_series(names.get(key, key), round(value, 4)) for key, value in ordered],
        [{"label": names.get(key, key), "auc": round(value, 5)} for key, value in ordered],
        "multi_roc_auc + paired_bootstrap",
        "AUC 只衡量排序；上线评审还要检查校准、稳定性和群体公平性。",
    )
''',
    "metric_registry": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    definitions: dict[str, list[dict]] = {}
    for row in rows:
        name = str(row.get("name", "")).strip()
        if name:
            definitions.setdefault(name, []).append(row)
    conflicts = []
    for name, items in definitions.items():
        hashes = {str(item.get("definition_hash", item.get("definition", ""))) for item in items}
        if len(hashes) > 1:
            conflicts.append({"label": name, "versions": len(hashes)})
    graph = {name: [str(dep) for dep in items[0].get("deps", [])] for name, items in definitions.items()}
    indegree = {name: 0 for name in graph}
    for name, deps in graph.items():
        for dep in deps:
            if dep in indegree:
                indegree[name] += 1
    queue = sorted([name for name, degree in indegree.items() if degree == 0])
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for other, deps in graph.items():
            if node in deps:
                indegree[other] -= 1
                if indegree[other] == 0:
                    queue.append(other)
    cyclic = len(order) != len(graph)
    return _envelope(
        f"登记 {len(graph)} 个指标，发现 {len(conflicts)} 个同名冲突",
        "依赖关系必须可拓扑排序；存在环时下游报表不得自动发布。",
        [
            _metric("指标数", len(graph), "个", "neutral"),
            _metric("同名冲突", len(conflicts), "个", "negative" if conflicts else "positive"),
            _metric("依赖环", 1 if cyclic else 0, "个", "negative" if cyclic else "positive"),
            _metric("可执行顺序", len(order), "个", "positive"),
        ],
        [_series(name, len(graph[name])) for name in order[:10]],
        [{"label": name, "deps": graph[name], "position": order.index(name) if name in order else -1}
         for name in sorted(graph)],
        "metric_dag + definition_hash_conflict",
        "定义哈希只能发现文本差异，口径等价性仍需数据域负责人复核。",
    )
''',
    "pivot_report": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    summary: dict[str, dict[str, float]] = {}
    for row in rows:
        region = str(row.get("region", "未分组"))
        period = str(row.get("period", "current"))
        bucket = summary.setdefault(region, {"base_orders": 0, "base_revenue": 0, "base_cost": 0,
                                              "cur_orders": 0, "cur_revenue": 0, "cur_cost": 0})
        prefix = "base" if period == "base" else "cur"
        bucket[f"{prefix}_orders"] += float(row.get("orders", 0))
        bucket[f"{prefix}_revenue"] += float(row.get("revenue", 0))
        bucket[f"{prefix}_cost"] += float(row.get("cost", 0))
    records = []
    for region, item in summary.items():
        base_price = item["base_revenue"] / max(item["base_orders"], 1)
        cur_price = item["cur_revenue"] / max(item["cur_orders"], 1)
        price_effect = (cur_price - base_price) * item["cur_orders"]
        volume_effect = (item["cur_orders"] - item["base_orders"]) * base_price
        base_profit = item["base_revenue"] - item["base_cost"]
        cur_profit = item["cur_revenue"] - item["cur_cost"]
        records.append({"label": region, "profit": cur_profit,
                        "margin": cur_profit / max(item["cur_revenue"], 1),
                        "price_effect": price_effect, "volume_effect": volume_effect,
                        "delta": cur_profit - base_profit})
    records.sort(key=lambda item: item["profit"], reverse=True)
    total_delta = sum(item["delta"] for item in records)
    price_total = sum(item["price_effect"] for item in records)
    volume_total = sum(item["volume_effect"] for item in records)
    return _envelope(
        f"利润变化 {total_delta:+,.0f} 元，价格贡献 {price_total:+,.0f}",
        "按线路区域汇总运单，并把利润变化拆为价格与业务量两因素。",
        [
            _metric("利润变化", total_delta, "元", "positive" if total_delta >= 0 else "negative"),
            _metric("价格贡献", price_total, "元", "neutral"),
            _metric("业务量贡献", volume_total, "元", "neutral"),
            _metric("区域数", len(records), "个", "neutral"),
        ],
        [_series(item["label"], round(item["delta"], 2)) for item in records],
        [{"label": item["label"], "profit": round(item["profit"], 2),
          "margin": round(item["margin"], 4), "price_effect": round(item["price_effect"], 2),
          "volume_effect": round(item["volume_effect"], 2)} for item in records],
        "weighted_pivot + price_volume_decomposition",
        "贡献拆解是会计恒等近似，跨区域调拨与临时附加费需另列口径。",
    )
''',
    "scheduled_delivery": r'''
def _next_cron_times(expression: str, count: int = 5) -> list[str]:
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError("cron 需要 5 个字段")
    minute, hour = fields[0], fields[1]
    if not minute.isdigit() or not hour.isdigit():
        raise ValueError("当前演示仅支持固定分钟和小时")
    now = datetime.now(timezone.utc).replace(minute=int(minute), hour=int(hour), second=0, microsecond=0)
    if now <= datetime.now(timezone.utc):
        now += timedelta(days=1)
    return [(now + timedelta(days=index)).isoformat() for index in range(count)]


def run_primary(rows: list[dict], config: dict) -> dict:
    sent = sum(float(row.get("sent", 0)) for row in rows)
    delivered = sum(float(row.get("delivered", 0)) for row in rows)
    opened = sum(float(row.get("opened", 0)) for row in rows)
    p = delivered / max(sent, 1)
    denominator = 1 + 1.96 ** 2 / max(sent, 1)
    center = (p + 1.96 ** 2 / (2 * max(sent, 1))) / denominator
    margin = 1.96 * math.sqrt(p * (1 - p) / max(sent, 1) + 1.96 ** 2 / (4 * sent ** 2)) / denominator
    cron = str(config.get("cron", "0 7 * * 1-5"))
    schedule = _next_cron_times(cron)
    open_rate = opened / max(delivered, 1)
    return _envelope(
        f"送达率 {p:.1%}，打开率 {open_rate:.1%}",
        f"cron `{cron}` 的下一次触发为 {schedule[0][:16]} UTC。",
        [
            _metric("送达率", p * 100, "%", "positive" if p > .95 else "negative"),
            _metric("Wilson 下限", max(center - margin, 0) * 100, "%", "neutral"),
            _metric("打开率", open_rate * 100, "%", "neutral"),
            _metric("投递总量", sent, "份", "neutral"),
        ],
        [_series(f"第 {index + 1} 次", 1) for index in range(len(schedule))],
        [{"label": f"触发 {index + 1}", "time_utc": value} for index, value in enumerate(schedule)],
        "cron_next_n + wilson_interval",
        "当前 cron 解析器支持固定分钟和小时；生产环境应接入完整调度器并处理时区。",
    )
''',
    "markov_attribution": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    paths = []
    for row in rows:
        path = row.get("path", [])
        if isinstance(path, list) and path:
            outcome = "Conversion" if int(row.get("converted", 1)) else "Null"
            paths.append(["Start"] + [str(item) for item in path] + [outcome])
    if len(paths) < 10:
        raise ValueError("转化路径不足")

    def transition_probability(remove_channel: str | None = None) -> float:
        counts: dict[str, dict[str, int]] = {}
        for path in paths:
            filtered = [state for state in path if state != remove_channel]
            for left, right in zip(filtered, filtered[1:]):
                counts.setdefault(left, {}).setdefault(right, 0)
                counts[left][right] += 1
        states = sorted(set(counts) | {target for edges in counts.values() for target in edges})
        transient = [state for state in states if state not in ("Conversion", "Null")]
        if "Start" not in transient:
            return 0.0
        index = {state: position for position, state in enumerate(transient)}
        q_matrix = np.zeros((len(transient), len(transient)), dtype=float)
        r_conversion = np.zeros(len(transient), dtype=float)
        for source, edges in counts.items():
            if source not in index:
                continue
            total = max(sum(edges.values()), 1)
            row = index[source]
            for target, count in edges.items():
                probability = count / total
                if target == "Conversion":
                    r_conversion[row] += probability
                elif target in index:
                    q_matrix[row, index[target]] += probability
        try:
            fundamental = np.linalg.inv(np.eye(len(transient)) - q_matrix)
        except np.linalg.LinAlgError:
            return 0.0
        return float(fundamental[index["Start"]] @ r_conversion)

    baseline = transition_probability(None)
    channels = sorted({channel for path in paths for channel in path[1:-1]})
    records = []
    for channel in channels:
        without = transition_probability(channel)
        records.append({"label": channel, "removal": abs(baseline - without) / max(baseline, 1e-9)})
    total = sum(item["removal"] for item in records) or 1
    for item in records:
        item["share"] = item["removal"] / total
    records.sort(key=lambda item: item["share"], reverse=True)
    top = records[0]
    return _envelope(
        f"{top['label']} 的移除效应最高，贡献 {top['share']:.1%}",
        f"基线 Markov 转化概率 {baseline:.1%}，按移除后的转化概率变化幅度归一化。",
        [
            _metric("基线转化", baseline * 100, "%", "neutral"),
            _metric("首要渠道", top["share"] * 100, "%", "positive"),
            _metric("渠道数", len(records), "个", "neutral"),
            _metric("路径数", len(paths), "条", "neutral"),
        ],
        [_series(item["label"], round(item["share"] * 100, 3)) for item in records],
        [{"label": item["label"], "removal_effect": round(item["removal"], 5),
          "share": round(item["share"], 5)} for item in records],
        "markov_transition + removal_effect",
        "归因依赖路径完整采集；离线曝光与跨设备身份合并偏差会改变结果。",
    )
''',
    "demand_forecast": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    values = np.asarray([float(row.get("demand", 0)) for row in rows], dtype=float)
    if len(values) < 28:
        raise ValueError("预测至少需要 28 天数据")
    season = 7
    level = float(np.mean(values[:season]))
    trend = float((np.mean(values[season:2 * season]) - np.mean(values[:season])) / season)
    seasonals = [float(values[i] - level) for i in range(season)]
    alpha, beta, gamma = .35, .08, .25
    fitted = []
    for index, value in enumerate(values):
        seasonal = seasonals[index % season]
        forecast = level + trend + seasonal
        fitted.append(forecast)
        old_level = level
        level = alpha * (value - seasonal) + (1 - alpha) * (level + trend)
        trend = beta * (level - old_level) + (1 - beta) * trend
        seasonals[index % season] = gamma * (value - level) + (1 - gamma) * seasonal
    forecast_values = [max(level + (step + 1) * trend + seasonals[(len(values) + step) % season], 0)
                       for step in range(7)]
    actual = values[-14:]
    predicted = np.asarray(fitted[-14:])
    mape = float(np.mean(np.abs((actual - predicted) / np.maximum(np.abs(actual), 1e-6))) * 100)
    return _envelope(
        f"未来七天日均需求 {np.mean(forecast_values):.0f} 份",
        f"Holt-Winters 加性模型，最近 14 天回测 MAPE {mape:.1f}%。",
        [
            _metric("七日总量", sum(forecast_values), "份", "neutral"),
            _metric("回测 MAPE", mape, "%", "positive" if mape < 12 else "negative"),
            _metric("趋势", trend, "份/天", "positive" if trend > 0 else "neutral"),
            _metric("历史天数", len(values), "天", "neutral"),
        ],
        [_series(f"D+{index + 1}", round(value, 2)) for index, value in enumerate(forecast_values)],
        [{"label": f"D+{index + 1}", "forecast": round(value, 2)}
         for index, value in enumerate(forecast_values)],
        "holt_winters_additive + rolling_mape",
        "促销、缺货和极端天气会影响可售量；建议把损耗目标作为约束而非直接乘系数。",
    )
''',
    "anomaly_review": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    matrix = np.asarray([
        [float(row.get("amount", 0)), (float(row.get("hour", 0)) / 24) * 2 * math.pi,
         math.sin((float(row.get("hour", 0)) / 24) * 2 * math.pi), float(row.get("velocity", 0))]
        for row in rows
    ])
    if len(matrix) < 30:
        raise ValueError("异常样本不足")
    contamination = float(config.get("contamination", .05))
    model = IsolationForest(contamination=contamination, random_state=42)
    labels = model.fit_predict(StandardScaler().fit_transform(matrix))
    raw = -model.score_samples(StandardScaler().fit(matrix).transform(matrix))
    median = np.median(raw)
    mad = np.median(np.abs(raw - median)) or 1
    robust_z = (raw - median) / (1.4826 * mad)
    indices = np.argsort(robust_z)[::-1]
    top = indices[0]
    records = [{"label": str(rows[idx].get("merchant", rows[idx].get("id", idx))),
                "score": float(raw[idx]), "z": float(robust_z[idx]),
                "flagged": bool(labels[idx] == -1)} for idx in indices[:20]]
    flagged_count = int((labels == -1).sum())
    return _envelope(
        f"标记 {flagged_count} 笔异常交易，最高稳健 z={robust_z[top]:.2f}",
        "Isolation Forest 负责排序，稳健 z-score 用于解释偏离强度。",
        [
            _metric("异常交易", flagged_count, "笔", "negative"),
            _metric("异常比例", flagged_count / len(rows) * 100, "%", "neutral"),
            _metric("最高 z", robust_z[top], "", "negative"),
            _metric("复核样本", len(rows), "笔", "neutral"),
        ],
        [_series(item["label"], round(item["score"], 4)) for item in records[:10]],
        records,
        "isolation_forest + robust_zscore",
        "无监督分数不是欺诈认定；复核员必须结合商户画像和资金链路。",
    )
''',
    "cohort_retention": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    cohorts = sorted({str(row.get("cohort", "2026-01")) for row in rows})
    periods = sorted({int(row.get("period", 0)) for row in rows})
    matrix = []
    for cohort in cohorts:
        row_map = {int(item.get("period", 0)): item for item in rows if str(item.get("cohort")) == cohort}
        base = float(row_map.get(0, {}).get("at_risk", 1))
        matrix.append({"label": cohort, "values": [
            round(float(row_map.get(period, {}).get("retained", 0)) / max(base, 1) * 100, 2)
            if period in row_map else 0 for period in periods
        ]})
    survival = 1.0
    curve = []
    for period in periods:
        at_risk = sum(float(row.get("at_risk", 0)) for row in rows if int(row.get("period", 0)) == period)
        retained = sum(float(row.get("retained", 0)) for row in rows if int(row.get("period", 0)) == period)
        events = max(at_risk - retained, 0)
        if at_risk > 0:
            survival *= 1 - events / at_risk
        curve.append({"label": f"P{period}", "value": round(survival * 100, 2)})
    latest_period = max(periods)
    latest = np.mean([item["values"][periods.index(latest_period)] for item in matrix])
    return _envelope(
        f"P{latest_period} 平均留存 {latest:.1f}%",
        f"共 {len(cohorts)} 个注册队列；Kaplan-Meier 用于处理尚未观察到的删失。",
        [
            _metric("队列数", len(cohorts), "个", "neutral"),
            _metric("最新留存", latest, "%", "positive" if latest > 30 else "neutral"),
            _metric("观察周期", len(periods), "期", "neutral"),
            _metric("生存概率", curve[-1]["value"], "%", "neutral"),
        ],
        curve,
        [{"label": item["label"], **{f"P{periods[i]}": value for i, value in enumerate(item["values"])}}
         for item in matrix],
        "cohort_matrix + kaplan_meier",
        "不同渠道获得用户的观察窗不一致；营销活动期需要单独标注。",
    )
''',
    "funnel_diagnosis": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    aggregated: dict[int, dict] = {}
    for row in rows:
        sequence = int(row.get("seq", 0))
        bucket = aggregated.setdefault(
            sequence,
            {"step": row.get("step", f"步骤{sequence + 1}"), "users": 0.0},
        )
        bucket["users"] += float(row.get("users", 0))
    ordered = [aggregated[key] for key in sorted(aggregated)]
    if len(ordered) < 2:
        raise ValueError("漏斗步骤不足")
    records = []
    baseline = max(float(ordered[0].get("users", 0)), 1)
    for index, row in enumerate(ordered):
        users = float(row.get("users", 0))
        previous = float(ordered[index - 1].get("users", users)) if index else users
        conversion = users / max(previous, 1)
        p = conversion
        denominator = 1 + 1.96 ** 2 / max(previous, 1)
        center = (p + 1.96 ** 2 / (2 * max(previous, 1))) / denominator
        margin = 1.96 * math.sqrt(p * (1 - p) / max(previous, 1) + 1.96 ** 2 / (4 * previous ** 2)) / denominator
        records.append({"label": str(row.get("step", f"步骤{index + 1}")),
                        "users": users, "conversion": conversion,
                        "low": max(center - margin, 0), "high": min(center + margin, 1),
                        "bottleneck": (1 - conversion) * (users / baseline)})
    worst = max(records[1:], key=lambda item: item["bottleneck"])
    overall = records[-1]["users"] / max(records[0]["users"], 1)
    return _envelope(
        f"最大瓶颈在 {worst['label']}，贡献评分 {worst['bottleneck']:.3f}",
        f"整体转化 {overall:.1%}；瓶颈评分同时考虑流失比例与剩余用户规模。",
        [
            _metric("整体转化", overall * 100, "%", "neutral"),
            _metric("最大瓶颈", worst["bottleneck"], "", "negative"),
            _metric("瓶颈步骤", len(records) - records.index(worst) - 1, "步后", "neutral"),
            _metric("入口用户", records[0]["users"], "人", "neutral"),
        ],
        [_series(item["label"], round(item["conversion"] * 100, 2)) for item in records],
        [{"label": item["label"], "users": int(item["users"]),
          "conversion": round(item["conversion"], 4), "low": round(item["low"], 4),
          "high": round(item["high"], 4), "bottleneck": round(item["bottleneck"], 4)} for item in records],
        "step_conversion + wilson + bottleneck_score",
        "漏斗步骤应来自同一事件口径；跨设备补全造成的回溯会改变历史转化。",
    )
''',
    "price_elasticity": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    prices = np.asarray([float(row.get("price", 0)) for row in rows], dtype=float)
    units = np.asarray([float(row.get("units", 0)) for row in rows], dtype=float)
    lines = np.asarray([str(row.get("line", "L1")) for row in rows])
    mask = (prices > 0) & (units > 0)
    x = np.log(prices[mask])
    y = np.log(units[mask])
    if len(x) < 10:
        raise ValueError("有效价格样本不足")
    slope, intercept = np.polyfit(x, y, 1)
    unique_lines = sorted(set(lines[mask].tolist()))
    rng = np.random.default_rng(42)
    boot = []
    for _ in range(300):
        sampled_lines = rng.choice(unique_lines, len(unique_lines), replace=True)
        idx = np.concatenate([np.where(lines[mask] == line)[0] for line in sampled_lines])
        try:
            boot.append(float(np.polyfit(x[idx], y[idx], 1)[0]))
        except np.linalg.LinAlgError:
            continue
    low, high = np.quantile(boot, [.025, .975])
    current_price = float(np.median(prices[mask]))
    current_units = float(np.median(units[mask]))
    new_units = current_units * ((current_price * 1.05 / current_price) ** slope)
    revenue_change = (current_price * 1.05 * new_units) / (current_price * current_units) - 1
    return _envelope(
        f"价格弹性估计 {slope:.3f}，95% 区间 [{low:.3f}, {high:.3f}]",
        f"票价上调 5% 在弹性不变假设下使收入变化 {revenue_change:+.1%}。",
        [
            _metric("价格弹性", slope, "", "negative" if slope < -1 else "neutral"),
            _metric("区间下限", low, "", "neutral"),
            _metric("区间上限", high, "", "neutral"),
            _metric("5% 收入影响", revenue_change * 100, "%", "positive" if revenue_change > 0 else "negative"),
        ],
        [_series(line, round(float(np.polyfit(x[lines[mask] == line], y[lines[mask] == line], 1)[0]), 4))
         if (lines[mask] == line).sum() > 2 else _series(line, 0) for line in unique_lines],
        [{"label": line, "n": int((lines[mask] == line).sum())} for line in unique_lines],
        "log_log_ols + cluster_bootstrap",
        "价格变化与客流季节可能同时发生；最终调价需结合对照线路。",
    )
''',
    "sample_bias": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    targets = {
        "age_group": {"18-29": .26, "30-44": .34, "45-59": .25, "60+": .15},
        "education": {"高中及以下": .35, "大专": .28, "本科": .29, "研究生": .08},
    }
    weights = np.ones(len(rows), dtype=float)
    frames = []
    for dimension, target in targets.items():
        values = np.asarray([str(row.get(dimension, "")) for row in rows])
        frame = {"dimension": dimension, "rows": values}
        frames.append(frame)
    for _ in range(80):
        for frame in frames:
            values = frame["rows"]
            for category, target_share in targets[frame["dimension"]].items():
                mask = values == category
                current = weights[mask].sum() / max(weights.sum(), 1)
                if current > 0:
                    weights[mask] *= target_share / current
        weights /= weights.mean()
    chi = 0.0
    before = []
    after = []
    for frame in frames:
        values = frame["rows"]
        for category, target_share in targets[frame["dimension"]].items():
            mask = values == category
            pre_share = float(mask.mean())
            post_share = float(weights[mask].sum() / weights.sum())
            before.append({"label": f"{frame['dimension']}:{category}", "value": pre_share})
            after.append({"label": f"{frame['dimension']}:{category}", "value": post_share})
            chi += (post_share - target_share) ** 2 / max(target_share, 1e-9)
    extreme = float(weights.max() / max(weights.min(), 1e-9))
    return _envelope(
        f"Raking 后最大权重比 {extreme:.2f}",
        "按年龄和教育两个维度迭代比例拟合，目标来自城市人口基准。",
        [
            _metric("校准维度", len(targets), "个", "neutral"),
            _metric("最大权重比", extreme, "倍", "negative" if extreme > 4 else "positive"),
            _metric("校准偏差", math.sqrt(chi / max(len(before), 1)), "", "neutral"),
            _metric("样本量", len(rows), "人", "neutral"),
        ],
        after,
        [{"label": item["label"], "before": round(before[i]["value"], 4),
          "after": round(item["value"], 4)} for i, item in enumerate(after)],
        "iterative_proportional_fitting + chi_square_deviation",
        "Raking 只能校准已观测维度；未响应偏差与覆盖误差仍需单独评估。",
    )
''',
    "batch_anova": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    groups: dict[str, list[float]] = {}
    for row in rows:
        try:
            groups.setdefault(str(row.get("line", "A线")), []).append(float(row["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    if len(groups) < 2:
        raise ValueError("至少需要两个产线组")
    values = list(groups.values())
    test = stats.f_oneway(*values)
    total_n = sum(len(item) for item in values)
    df_within = total_n - len(values)
    mse = sum(np.var(item, ddof=1) * (len(item) - 1) for item in values) / max(df_within, 1)
    names = sorted(groups)
    pairs = []
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            diff = float(np.mean(groups[left]) - np.mean(groups[right]))
            se = math.sqrt(mse * (1 / len(groups[left]) + 1 / len(groups[right])))
            q_value = abs(diff) / max(se, 1e-9) * math.sqrt(2)
            p_value = float(stats.studentized_range.sf(q_value, len(values), max(df_within, 1)))
            pairs.append({"left": left, "right": right, "diff": diff, "p_value": p_value})
    pairs.sort(key=lambda item: abs(item["diff"]), reverse=True)
    top = pairs[0]
    return _envelope(
        f"ANOVA p={test.pvalue:.4f}，最大差异 {top['left']} vs {top['right']}",
        f"Tukey 成对比较中最小 p={min(item['p_value'] for item in pairs):.4f}。",
        [
            _metric("ANOVA p 值", test.pvalue, "", "positive" if test.pvalue < .05 else "neutral"),
            _metric("最大均值差", top["diff"], "", "negative" if abs(top["diff"]) > 0 else "neutral"),
            _metric("Tukey 最小 p", min(item["p_value"] for item in pairs), "", "neutral"),
            _metric("总样本", total_n, "份", "neutral"),
        ],
        [_series(name, round(float(np.mean(groups[name])), 4)) for name in names],
        [{"label": f"{item['left']} vs {item['right']}", "mean_diff": round(item["diff"], 4),
          "p_value": round(item["p_value"], 5)} for item in pairs],
        "one_way_anova + tukey_hsd",
        "检测样本应满足独立抽样假设；同一批次重复测量需要改用混合模型。",
    )
''',
    "threshold_tuning": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    target = np.asarray([int(row.get("y", 0)) for row in rows])
    score = np.asarray([float(row.get("score", 0)) for row in rows])
    if len(set(target.tolist())) < 2:
        raise ValueError("需要正负样本")
    fpr, tpr, thresholds = roc_curve(target, score)
    j_scores = tpr - fpr
    index = int(np.argmax(j_scores))
    threshold = float(thresholds[index])
    predicted = (score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(target, predicted).ravel()
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    pass_rate = float((score >= threshold).mean())
    return _envelope(
        f"Youden J 最优阈值 {threshold:.3f}，通过率 {pass_rate:.1%}",
        f"命中 Recall {recall:.1%}，精确率 {precision:.1%}；业务还需设定可接受坏账成本。",
        [
            _metric("最优阈值", threshold, "", "positive"),
            _metric("Recall", recall * 100, "%", "positive"),
            _metric("Precision", precision * 100, "%", "neutral"),
            _metric("通过率", pass_rate * 100, "%", "neutral"),
        ],
        [{"label": f"TPR {tpr[i]:.2f}", "value": float(tpr[i])} for i in np.linspace(0, len(tpr) - 1, 10, dtype=int)],
        [{"label": "混淆矩阵", "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
          "threshold": round(threshold, 5)}],
        "roc_curve + youden_j + confusion_matrix",
        "历史标签存在表现期偏差；上线阈值要按近期样本和业务成本重新评审。",
    )
''',
    "decision_rules": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    feature_keys = ["age", "seniority", "alerts", "days_since_service", "usage"]
    matrix = np.asarray([[float(row.get(key, 0)) for key in feature_keys] for row in rows])
    target = np.asarray([int(row.get("late", 0)) for row in rows])
    if len(set(target.tolist())) < 2:
        raise ValueError("需要超时与非超时样本")
    tree = DecisionTreeClassifier(max_depth=4, min_samples_leaf=max(8, len(rows) // 40), random_state=42)
    tree.fit(matrix, target)
    paths = []

    def walk(node: int, conditions: list[str]) -> None:
        if tree.tree_.children_left[node] == tree.tree_.children_right[node]:
            paths.append({"label": " 且 ".join(conditions) if conditions else "全部工单",
                          "rate": float(tree.tree_.value[node][0][1] / max(tree.tree_.value[node][0].sum(), 1)),
                          "samples": int(tree.tree_.n_node_samples[node])})
            return
        feature = feature_keys[tree.tree_.feature[node]]
        threshold = tree.tree_.threshold[node]
        walk(tree.tree_.children_left[node], conditions + [f"{feature} <= {threshold:.1f}"])
        walk(tree.tree_.children_right[node], conditions + [f"{feature} > {threshold:.1f}"])

    walk(0, [])
    paths.sort(key=lambda item: item["rate"], reverse=True)
    top = paths[0]
    predicted = tree.predict(matrix)
    accuracy = float((predicted == target).mean())
    return _envelope(
        f"最高风险规则命中率 {top['rate']:.1%}，样本 {top['samples']} 单",
        f"CART 树最大深度 4，训练集准确率 {accuracy:.1%}；叶节点规则可复核。",
        [
            _metric("训练准确率", accuracy * 100, "%", "neutral"),
            _metric("规则数量", len(paths), "条", "neutral"),
            _metric("最高风险叶", top["rate"] * 100, "%", "negative"),
            _metric("叶样本", top["samples"], "单", "neutral"),
        ],
        [_series(f"规则 {i + 1}", round(item["rate"] * 100, 2)) for i, item in enumerate(paths[:10])],
        [{"label": item["label"], "late_rate": round(item["rate"], 4),
          "samples": item["samples"]} for item in paths],
        "cart_decision_tree + rule_path_export",
        "规则来自训练集，需在后续工单上做时间外验证；叶节点过小时不应直接上线。",
    )
''',
    "topic_clusters": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    texts = [str(row.get("text", "")).strip() for row in rows if str(row.get("text", "")).strip()]
    if len(texts) < 20:
        raise ValueError("投诉文本不足")
    vectorizer = TfidfVectorizer(max_features=600, ngram_range=(1, 2), min_df=2)
    matrix = vectorizer.fit_transform(texts)
    topics = int(config.get("topics", 4))
    model = NMF(n_components=topics, init="nndsvda", random_state=42, max_iter=500)
    weights = model.fit_transform(matrix)
    labels = weights.argmax(axis=1)
    feature_names = vectorizer.get_feature_names_out()
    topic_records = []
    for topic in range(topics):
        indices = np.argsort(model.components_[topic])[::-1][:6]
        topic_records.append({"label": f"主题 {topic + 1}",
                              "keywords": [feature_names[index] for index in indices],
                              "size": int((labels == topic).sum())})
    sample_size = min(400, matrix.shape[0])
    silhouette = silhouette_score(matrix[:sample_size], labels[:sample_size]) if len(set(labels[:sample_size])) > 1 else 0
    topic_records.sort(key=lambda item: item["size"], reverse=True)
    return _envelope(
        f"归纳 {topics} 个客诉主题，最大主题 {topic_records[0]['size']} 条",
        f"TF-IDF + NMF 样本轮廓系数 {silhouette:.3f}；关键词由主题载荷最高的词组成。",
        [
            _metric("主题数", topics, "个", "neutral"),
            _metric("最大主题占比", topic_records[0]["size"] / len(texts) * 100, "%", "neutral"),
            _metric("轮廓系数", silhouette, "", "positive" if silhouette > .05 else "neutral"),
            _metric("文本量", len(texts), "条", "neutral"),
        ],
        [_series(item["label"], item["size"]) for item in topic_records],
        [{"label": item["label"], "keywords": ",".join(item["keywords"]), "size": item["size"]}
         for item in topic_records],
        "tfidf + nmf_topic_model",
        "主题词是归纳辅助，不应直接作为处罚依据；中文分词与否定语义仍是已知差异。",
    )
''',
    "geo_hotspots": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    coords = np.asarray([[float(row.get("lat", 0)), float(row.get("lng", 0))] for row in rows])
    if len(coords) < 30:
        raise ValueError("配送点不足")
    scaled = StandardScaler().fit_transform(coords)
    neighbors = NearestNeighbors(n_neighbors=min(8, len(coords))).fit(scaled)
    distances, _ = neighbors.kneighbors(scaled)
    # Approximate metres so the UI and operator can interpret the radius.
    meter_factor = 111_000.0
    k_distance = distances[:, -1] * meter_factor / 100
    eps = float(np.quantile(k_distance, .9) / meter_factor * 100)
    model = DBSCAN(eps=max(eps, 1e-5), min_samples=int(config.get("min_samples", 5)))
    labels = model.fit_predict(scaled)
    cluster_records = []
    for label in sorted(set(labels)):
        if label == -1:
            continue
        subset = coords[labels == label]
        cluster_records.append({"label": f"热区 {label + 1}", "size": int(len(subset)),
                                "lat": round(float(subset[:, 0].mean()), 5),
                                "lng": round(float(subset[:, 1].mean()), 5)})
    cluster_records.sort(key=lambda item: item["size"], reverse=True)
    noise = int((labels == -1).sum())
    return _envelope(
        f"识别 {len(cluster_records)} 个热区，{noise} 个离散点",
        f"DBSCAN eps={eps:.5f}（标准化空间），最小样本 {config.get('min_samples', 5)}。",
        [
            _metric("热区数", len(cluster_records), "个", "positive"),
            _metric("最大热区", cluster_records[0]["size"] if cluster_records else 0, "单", "neutral"),
            _metric("离散点", noise, "单", "negative"),
            _metric("总点数", len(coords), "单", "neutral"),
        ],
        [_series(item["label"], item["size"]) for item in cluster_records],
        cluster_records,
        "dbscan + k_distance_radius",
        "经纬度在标准化空间聚类会轻微拉伸距离；正式派单应使用投影坐标和路网可达时间。",
    )
''',
    "sample_size": r'''
def run_primary(rows: list[dict], config: dict) -> dict:
    baseline = float(config.get("baseline", .12))
    mde = float(config.get("mde", .02))
    alpha = float(config.get("alpha", .05))
    power = float(config.get("power", .8))
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    variant = baseline + mde

    def required(mde_value: float) -> int:
        p2 = baseline + mde_value
        pooled = (baseline + p2) / 2
        numerator = z_alpha * math.sqrt(2 * pooled * (1 - pooled)) + z_power * math.sqrt(
            baseline * (1 - baseline) + p2 * (1 - p2))
        return int(math.ceil((numerator / max(mde_value, 1e-9)) ** 2))

    per_group = required(mde)
    total = per_group * 2
    daily_traffic = float(config.get("daily_traffic", 900))
    allocation = float(config.get("allocation", .5))
    days = math.ceil(total / max(daily_traffic * allocation, 1))
    curve = [{"label": f"MDE {value:.1%}", "value": required(value)} for value in
             (mde * .5, mde * .75, mde, mde * 1.25, mde * 1.5)]
    return _envelope(
        f"每组需要 {per_group:,} 人，预计 {days} 天",
        f"基线 {baseline:.1%}，MDE {mde:.1%}，alpha={alpha:.2f}，power={power:.1%}。",
        [
            _metric("每组样本", per_group, "人", "neutral"),
            _metric("总样本", total, "人", "neutral"),
            _metric("预计天数", days, "天", "positive" if days <= 14 else "negative"),
            _metric("目标效应", mde * 100, "%", "neutral"),
        ],
        curve,
        [{"label": item["label"], "sample_per_group": item["value"]} for item in curve],
        "two_proportion_power + mde_root_search",
        "样本量基于双侧独立比例检验；分流污染、SRM 和多指标校正会增加实际预算。",
    )
''',
}


def analysis_engine_source(project: dict) -> str:
    body = ALGORITHM_SOURCES[project["algorithm"]]
    return f'''
import itertools
import math
from datetime import datetime, timedelta, timezone

import numpy as np
from scipy import stats
from sklearn.cluster import DBSCAN, KMeans
from sklearn.ensemble import IsolationForest
from sklearn.feature_selection import mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve, silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer


def _metric(label, value, unit="", tone="neutral"):
    if isinstance(value, (np.floating, np.integer)):
        value = value.item()
    return {{"label": label, "value": value, "unit": unit, "tone": tone}}


def _series(label, value):
    return {{"label": str(label), "value": float(value)}}


def _envelope(headline, narrative, metrics, series, table, method, caveat):
    return {{
        "headline": headline,
        "narrative": narrative,
        "metrics": metrics,
        "series": series,
        "table": table,
        "method": method,
        "caveat": caveat,
    }}

{body}


def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {{}})
'''


DEMO_SOURCES = {
    "ab_decision": r'''
def demo_rows():
    rng = np.random.default_rng(1001)
    rows = []
    for index in range(4800):
        group = "A-对照" if index % 2 == 0 else "B-长醒发"
        rate = .112 if group.startswith("A") else .132
        rows.append({"user_id": f"m{index:05d}", "group": group, "exposure": 1,
                     "conversion": int(rng.random() < rate), "store": f"S{index % 42:02d}"})
    return rows
''',
    "correlation_diag": r'''
def demo_rows():
    rng = np.random.default_rng(1002)
    rows = []
    pairs = ["温度-湿度", "门磁-温度", "振动-电流", "回风-蒸发压力", "霜层-换热效率"]
    for index in range(4800):
        pair = pairs[index % len(pairs)]
        x = float(rng.normal(0, 1))
        rho = [.76, -.48, .62, .35, -.67][index % len(pairs)]
        y = float(rho * x + rng.normal(0, .75))
        rows.append({"pair": pair, "x": round(x, 5), "y": round(y, 5),
                     "warehouse": f"W{index % 18:02d}", "ts": f"2026-10-{index % 28 + 1:02d}T{(index // 28) % 24:02d}:00:00Z"})
    return rows
''',
    "hypothesis_batch": r'''
def demo_rows():
    rng = np.random.default_rng(1003)
    rows = []
    effects = {"A-习惯": 0, "B-深播": .42, "C-膜下滴灌": .73, "D-减氮": -.18, "E-晚播": -.51}
    for index in range(4200):
        batch = list(effects)[index % 5]
        value = 7.4 + effects[batch] + rng.normal(0, 1.15)
        rows.append({"batch": batch, "value": round(float(value), 4),
                     "field": f"F{index % 31:02d}", "season": 2026})
    return rows
''',
    "drift_monitor": r'''
def demo_rows():
    rng = np.random.default_rng(1004)
    rows = []
    for index in range(4800):
        period = "reference" if index % 2 == 0 else "current"
        value = rng.normal(5.3, .44) if period == "reference" else rng.normal(5.55, .61)
        rows.append({"period": period, "value": round(float(value), 4),
                     "lab": f"LAB-{index % 9 + 1}", "reagent": "R2409" if period == "reference" else "R2410"})
    return rows
''',
    "segment_kmeans": r'''
def demo_rows():
    rng = np.random.default_rng(1005)
    rows = []
    centers = [(8, 18, 1600), (28, 7, 620), (72, 2, 180)]
    for index in range(3000):
        center = centers[index % 3]
        rows.append({"member_id": f"VIP{index:05d}",
                     "recency": max(1, round(rng.normal(center[0], center[0] * .16))),
                     "frequency": max(1, round(rng.normal(center[1], center[1] * .2))),
                     "monetary": max(20, round(rng.normal(center[2], center[2] * .18), 2)),
                     "store": f"S{index % 86:03d}"})
    return rows
''',
    "basket_rules": r'''
def demo_rows():
    rng = np.random.default_rng(1006)
    base = ["咖啡", "饭团", "面包", "牛奶", "茶叶蛋", "矿泉水", "关东煮", "口香糖"]
    rows = []
    for index in range(2200):
        items = list(rng.choice(base, size=int(rng.integers(1, 4)), replace=False))
        if "咖啡" in items and "面包" not in items and rng.random() < .58:
            items.append("面包")
        if "饭团" in items and "茶叶蛋" not in items and rng.random() < .46:
            items.append("茶叶蛋")
        rows.append({"basket_id": f"B{index:05d}", "items": items,
                     "store": f"N{index % 120:03d}", "hour": int(rng.integers(18, 24))})
    return rows
''',
    "churn_model": r'''
def demo_rows():
    rng = np.random.default_rng(1007)
    rows = []
    for index in range(3200):
        tenure = float(rng.integers(2, 48))
        usage = float(max(0, rng.normal(21, 8)))
        tickets = float(rng.poisson(1.4))
        gap = float(max(0, rng.normal(9, 7)))
        logit = -.08 * tenure - .11 * usage + .45 * tickets + .16 * gap - 1.9
        probability = 1 / (1 + math.exp(-logit))
        rows.append({"account_id": f"AC{index:05d}", "tenure": tenure,
                     "usage": round(usage, 2), "tickets": tickets,
                     "login_gap": round(gap, 2), "churned": int(rng.random() < probability)})
    return rows
''',
    "feature_select": r'''
def demo_rows():
    rng = np.random.default_rng(1008)
    rows = []
    for index in range(3000):
        f1 = rng.normal()
        f2 = rng.normal()
        f3 = .87 * f1 + rng.normal(0, .4)
        f4 = rng.normal()
        f5 = rng.normal()
        signal = 1.15 * f1 - .72 * f2 + .18 * f4 + rng.normal(0, .7)
        rows.append({"device_id": f"D{index:05d}", "f_1": round(float(f1), 5),
                     "f_2": round(float(f2), 5), "f_3": round(float(f3), 5),
                     "f_4": round(float(f4), 5), "f_5": round(float(f5), 5),
                     "label": int(signal > 0)})
    return rows
''',
    "model_compare": r'''
def demo_rows():
    rng = np.random.default_rng(1009)
    rows = []
    for index in range(2800):
        latent = rng.normal()
        y = int(latent + rng.normal(0, .9) > .25)
        p_base = 1 / (1 + np.exp(-(.75 * latent + rng.normal(0, 1.1))))
        p_tree = 1 / (1 + np.exp(-(1.05 * latent + rng.normal(0, .8))))
        p_logit = 1 / (1 + np.exp(-(.92 * latent + rng.normal(0, .95))))
        rows.append({"id": f"E{index:05d}", "y": y,
                     "p_base": round(float(p_base), 6), "p_tree": round(float(p_tree), 6),
                     "p_logit": round(float(p_logit), 6)})
    return rows
''',
    "metric_registry": r'''
def demo_rows():
    metrics = [
        ("日活跃用户", "count(distinct user_id)", [], "a1"),
        ("7日留存", "cohort_retention(d7)", ["日活跃用户"], "b2"),
        ("付费转化率", "paying/active", ["日活跃用户"], "c3"),
        ("ARPU", "revenue/active", ["付费转化率"], "d4"),
        ("广告收入", "sum(ad_revenue)", [], "e5"),
        ("会员收入", "sum(member_revenue)", [], "f6"),
        ("总收入", "广告收入+会员收入", ["广告收入", "会员收入"], "g7"),
        ("内容消费深度", "watched_minutes/active", ["日活跃用户"], "h8"),
        ("次留", "retained_day1/new_users", ["日活跃用户"], "i9"),
        ("净收入", "总收入-refund", ["总收入"], "j10"),
    ]
    rows = []
    for index, (name, definition, deps, digest) in enumerate(metrics, 1):
        rows.append({"name": name, "definition": definition, "definition_hash": digest,
                     "deps": deps, "domain": "内容" if index < 8 else "商业", "version": 1})
    rows.append({"name": "总收入", "definition": "广告收入 + 会员收入 + 其他收入",
                 "definition_hash": "alt_total", "deps": ["广告收入", "会员收入"],
                 "domain": "商业", "version": 2})
    return rows
''',
    "pivot_report": r'''
def demo_rows():
    rng = np.random.default_rng(1011)
    regions = ["沪苏", "浙皖", "闽赣", "鲁豫", "湘鄂", "川渝", "京津冀", "粤港澳"]
    rows = []
    for index in range(4000):
        region = regions[index % len(regions)]
        period = "base" if index % 2 == 0 else "current"
        orders = int(rng.integers(80, 210))
        price = 730 + regions.index(region) * 27 + rng.normal(0, 18)
        if period == "current":
            orders = int(orders * rng.uniform(.91, 1.12))
            price *= rng.uniform(1.01, 1.07)
        rows.append({"region": region, "period": period, "orders": orders,
                     "revenue": round(orders * price, 2),
                     "cost": round(orders * price * rng.uniform(.73, .87), 2),
                     "customer": f"C{index % 38:02d}"})
    return rows
''',
    "scheduled_delivery": r'''
def demo_rows():
    rng = np.random.default_rng(1012)
    regions = ["东区", "南区", "西区", "北区", "中心区", "近郊"]
    rows = []
    for index in range(1600):
        sent = int(rng.integers(30, 180))
        delivered = int(sent * rng.uniform(.92, .995))
        opened = int(delivered * rng.uniform(.38, .72))
        rows.append({"report_name": f"{regions[index % 6]}晨报", "region": regions[index % 6],
                     "sent": sent, "delivered": delivered, "opened": opened,
                     "cron": "0 7 * * 1-5", "batch": f"2026-11-{index % 13 + 1:02d}"})
    return rows
''',
    "markov_attribution": r'''
def demo_rows():
    rng = np.random.default_rng(1013)
    channels = ["开屏", "优惠券", "搜索", "私域", "内容种草"]
    rows = []
    for index in range(3000):
        path = []
        for _ in range(int(rng.integers(2, 6))):
            path.append(str(rng.choice(channels)))
        path = list(dict.fromkeys(path))
        conversion_probability = .10
        conversion_probability += .07 if "优惠券" in path else 0
        conversion_probability += .05 if "搜索" in path else 0
        rows.append({"path_id": f"P{index:05d}", "path": path,
                     "converted": int(rng.random() < conversion_probability),
                     "city": ["上海", "杭州", "南京"][index % 3]})
    return rows
''',
    "demand_forecast": r'''
def demo_rows():
    rng = np.random.default_rng(1014)
    rows = []
    for store in range(4):
        for index in range(120):
            weekday = index % 7
            demand = 135 + index * .26 + (24 if weekday in (5, 6) else 0) + rng.normal(0, 9)
            rows.append({"date": f"2026-{7 + index // 30:02d}-{index % 30 + 1:02d}",
                         "demand": max(50, round(float(demand))), "store": f"Q{store + 1}",
                         "sku": "有机生菜" if store % 2 == 0 else "低温鲜奶"})
    return rows
''',
    "anomaly_review": r'''
def demo_rows():
    rng = np.random.default_rng(1015)
    rows = []
    for index in range(3200):
        anomalous = index % 63 == 0
        amount = float(rng.lognormal(8.1, .7))
        hour = int(rng.integers(0, 6))
        velocity = float(rng.normal(1.2, .4))
        if anomalous:
            amount *= rng.uniform(5, 12)
            velocity *= rng.uniform(3, 7)
        rows.append({"id": f"TX{index:06d}", "merchant": f"M{index % 480:04d}",
                     "amount": round(amount, 2), "hour": hour,
                     "velocity": round(max(0, velocity), 4)})
    return rows
''',
    "cohort_retention": r'''
def demo_rows():
    rng = np.random.default_rng(1016)
    rows = []
    for cohort_index in range(12):
        size = int(rng.integers(900, 1800))
        survival = 1.0
        for period in range(12):
            if period > 0:
                survival *= rng.uniform(.76, .94)
            retained = int(size * survival)
            rows.append({"cohort": f"2025-{cohort_index + 1:02d}", "period": period,
                         "at_risk": size, "retained": retained})
    return rows
''',
    "funnel_diagnosis": r'''
def demo_rows():
    rng = np.random.default_rng(1017)
    rows = []
    steps = [("进入开户", 10000, 0), ("身份认证", 8400, 1), ("活体检测", 7050, 2),
             ("绑定银行卡", 5020, 3), ("首笔转入", 4180, 4), ("完成激活", 3960, 5)]
    for channel in ["自然流量", "投放", "合作渠道"]:
        for step, users, seq in steps:
            adjusted = int(users * (1.0 if channel == "自然流量" else .76 if channel == "投放" else .52))
            adjusted = int(adjusted * rng.uniform(.98, 1.02))
            rows.append({"step": step, "users": adjusted, "seq": seq, "channel": channel})
    return rows
''',
    "price_elasticity": r'''
def demo_rows():
    rng = np.random.default_rng(1018)
    rows = []
    lines = ["沪宁", "沪杭", "杭甬", "苏锡", "合宁", "甬台", "温福", "金义"]
    for index in range(3200):
        line = lines[index % len(lines)]
        base_price = 68 + lines.index(line) * 7
        price = max(20, base_price * rng.uniform(.86, 1.18))
        elasticity = -1.25 + lines.index(line) * .035
        units = 1000 * (price / base_price) ** elasticity * rng.lognormal(0, .08)
        rows.append({"line": line, "price": round(price, 2), "units": round(units, 2),
                     "period": "2026-W" + str(index % 32 + 1).zfill(2)})
    return rows
''',
    "sample_bias": r'''
def demo_rows():
    rng = np.random.default_rng(1019)
    rows = []
    for index in range(2200):
        age = str(rng.choice(["18-29", "30-44", "45-59", "60+"], p=[.38, .39, .17, .06]))
        education = str(rng.choice(["高中及以下", "大专", "本科", "研究生"], p=[.18, .25, .43, .14]))
        rows.append({"respondent": f"R{index:05d}", "age_group": age, "education": education,
                     "region": ["中心", "近郊", "远郊"][index % 3],
                     "mode": "公交" if index % 4 else "自驾", "base_weight": 1.0})
    return rows
''',
    "batch_anova": r'''
def demo_rows():
    rng = np.random.default_rng(1020)
    rows = []
    lines = {"A线": 4.2, "B线": 4.31, "C线": 4.16, "D线": 4.49, "E线": 4.25}
    for index in range(2200):
        line = list(lines)[index % 5]
        value = np.random.default_rng(1020 + index).normal(lines[line], .38)
        rows.append({"line": line, "batch": f"B{index // 5 % 3 + 1}", "value": round(float(value), 4),
                     "metric": "含水率"})
    return rows
''',
    "threshold_tuning": r'''
def demo_rows():
    rng = np.random.default_rng(1021)
    rows = []
    for index in range(3400):
        latent = rng.normal()
        y = int(latent + rng.normal(0, .85) > .6)
        score = 1 / (1 + np.exp(-(1.1 * latent + rng.normal(0, .75))))
        rows.append({"application_id": f"AP{index:05d}", "y": y, "score": round(float(score), 6),
                     "product": ["现金分期", "消费贷"][index % 2]})
    return rows
''',
    "decision_rules": r'''
def demo_rows():
    rng = np.random.default_rng(1022)
    rows = []
    for index in range(2800):
        age = int(rng.integers(1, 14))
        seniority = int(rng.integers(1, 20))
        alerts = int(rng.poisson(2.1))
        days = int(rng.integers(1, 180))
        usage = float(rng.normal(7.5, 2.4))
        risk = .34 * age - .18 * seniority + .61 * alerts + .018 * days - .21 * usage - 1.3
        late = int(rng.random() < 1 / (1 + math.exp(-risk)))
        rows.append({"work_order": f"WO{index:05d}", "age": age, "seniority": seniority,
                     "alerts": alerts, "days_since_service": days,
                     "usage": round(usage, 3), "late": late})
    return rows
''',
    "topic_clusters": r'''
def demo_rows():
    rng = np.random.default_rng(1023)
    templates = [
        "司机绕路 路线 偏航 导航 不准", "车内异味 清洁 座椅 卫生", "司机态度 冷漠 催促 沟通 差",
        "等待太久 接驾 慢 排队 时间", "费用异常 附加费 扣款 账单 不明", "定位不准 上车点 找不到 地图",
        "司机取消 订单 取消 频繁 接单", "发票 无法 开具 行程 报销 问题",
    ]
    rows = []
    for index in range(1600):
        template = templates[index % len(templates)]
        words = template.split()
        text = "".join(str(rng.choice(words)) + "，" for _ in range(int(rng.integers(3, 7))))
        rows.append({"ticket_id": f"T{index:05d}", "text": text.rstrip("，"),
                     "business": ["快车", "专车", "顺风"][index % 3],
                     "city": ["上海", "杭州", "南京"][index % 3]})
    return rows
''',
    "geo_hotspots": r'''
def demo_rows():
    rng = np.random.default_rng(1024)
    centers = [(31.2304, 121.4737), (31.220, 121.52), (31.19, 121.43), (31.27, 121.47)]
    rows = []
    for index in range(4200):
        if index % 41 == 0:
            lat = 31.15 + rng.uniform(0, .22)
            lng = 121.30 + rng.uniform(0, .28)
        else:
            center = centers[index % len(centers)]
            lat = center[0] + rng.normal(0, .007)
            lng = center[1] + rng.normal(0, .009)
        rows.append({"order_id": f"O{index:06d}", "lat": round(float(lat), 6),
                     "lng": round(float(lng), 6), "amount": round(float(rng.lognormal(3.2, .5)), 2),
                     "station": f"ST{index % 18:02d}"})
    return rows
''',
    "sample_size": r'''
def demo_rows():
    return [
        {"design": "会员首购", "baseline": .12, "mde": .02, "daily_traffic": 900},
        {"design": "搜索点击", "baseline": .28, "mde": .015, "daily_traffic": 4200},
        {"design": "试用转付费", "baseline": .08, "mde": .01, "daily_traffic": 1600},
        {"design": "复购频次", "baseline": .31, "mde": .025, "daily_traffic": 2400},
    ]
''',
}


def demo_data_source(project: dict) -> str:
    body = DEMO_SOURCES[project["algorithm"]]
    return f'''
import math

import numpy as np


{body}
'''


def backend_runtime_files(project: dict) -> dict[str, str]:
    short = project["short"]
    files: dict[str, str] = {}
    files["src/utils/security.py"] = """
import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from src.config import settings


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return f"pbkdf2_sha256$210000${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt_b64, digest_b64 = encoded.split("$", 3)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, role: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_expiry_minutes)
    payload = {"sub": user_id, "role": role, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
"""
    files["src/middlewares/auth.py"] = """
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User
from src.utils.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少访问令牌")
    payload = decode_access_token(credentials.credentials)
    user = db.get(User, payload.get("sub")) if payload else None
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="访问令牌无效")
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前角色无此操作权限")
        return user
    return dependency
"""
    files["src/middlewares/rate_limit.py"] = """
import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = 180, window_seconds: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window_seconds
        self.calls = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path.endswith("/health"):
            return await call_next(request)
        key = request.headers.get("authorization", request.client.host if request.client else "unknown")
        now = time.monotonic()
        queue = self.calls[key]
        while queue and now - queue[0] > self.window:
            queue.popleft()
        if len(queue) >= self.limit:
            return JSONResponse(status_code=429, content={"detail": "请求过于频繁，请稍后再试"})
        queue.append(now)
        return await call_next(request)
"""
    files["src/middlewares/errors.py"] = """
import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "服务处理失败，请稍后重试"})
"""
    files["src/services/auth_service.py"] = """
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.user import User
from src.utils.security import create_access_token, verify_password


def authenticate(db: Session, email: str, password: str) -> tuple[User, str] | None:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user, create_access_token(user.id, user.role)
"""
    files["src/services/audit_service.py"] = """
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog


def record(db: Session, action: str, resource_type: str, resource_id: str,
           actor_id: str, detail: dict | None = None) -> AuditLog:
    entry = AuditLog(action=action, resource_type=resource_type,
                     resource_id=resource_id, actor_id=actor_id, detail=detail or {})
    db.add(entry)
    return entry


def list_recent(db: Session, limit: int = 100) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)))
"""
    files["src/services/dataset_service.py"] = """
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.dataset import Dataset
from src.models.workspace import Workspace


def list_datasets(db: Session) -> list[Dataset]:
    return list(db.scalars(select(Dataset).order_by(Dataset.created_at.desc())))


def get_dataset(db: Session, dataset_id: str) -> Dataset | None:
    return db.get(Dataset, dataset_id)


def create_dataset(db: Session, workspace: Workspace, user_id: str,
                   name: str, source: str, description: str, rows: list[dict]) -> Dataset:
    serialized = json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()
    natural_key = f"{workspace.id}:{name}:{hashlib.sha1(serialized).hexdigest()[:12]}"
    existing = db.scalar(select(Dataset).where(Dataset.natural_key == natural_key))
    if existing:
        return existing
    item = Dataset(
        natural_key=natural_key,
        name=name,
        source=source,
        description=description,
        rows=rows,
        row_count=len(rows),
        checksum=hashlib.sha256(serialized).hexdigest(),
        workspace_id=workspace.id,
        created_by=user_id,
        status="ready",
    )
    db.add(item)
    db.flush()
    return item
"""
    files["src/services/analysis_service.py"] = """
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.analysis import Analysis
from src.models.workspace import Workspace


def list_analyses(db: Session) -> list[Analysis]:
    return list(db.scalars(select(Analysis).order_by(Analysis.created_at.desc())))


def get_analysis(db: Session, analysis_id: str) -> Analysis | None:
    return db.get(Analysis, analysis_id)


def create_analysis(db: Session, workspace: Workspace, user_id: str,
                    name: str, dataset_id: str, kind: str, hypothesis: str,
                    config: dict) -> Analysis:
    natural_key = f"{workspace.id}:{name}:{kind}"
    existing = db.scalar(select(Analysis).where(Analysis.natural_key == natural_key))
    if existing:
        return existing
    item = Analysis(
        natural_key=natural_key,
        name=name,
        kind=kind,
        hypothesis=hypothesis,
        config=config,
        dataset_id=dataset_id,
        workspace_id=workspace.id,
        created_by=user_id,
        status="ready",
    )
    db.add(item)
    db.flush()
    return item
"""
    files["src/services/run_service.py"] = """
import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.analysis import Analysis
from src.models.analysis_run import AnalysisRun
from src.models.comment import Comment
from src.models.dataset import Dataset
from src.services.analysis_engine import run_algorithm


def list_runs(db: Session) -> list[AnalysisRun]:
    return list(db.scalars(select(AnalysisRun).order_by(AnalysisRun.created_at.desc())))


def get_run(db: Session, run_id: str) -> AnalysisRun | None:
    return db.get(AnalysisRun, run_id)


def execute_run(db: Session, analysis: Analysis, actor_id: str) -> AnalysisRun:
    dataset = db.get(Dataset, analysis.dataset_id)
    if not dataset:
        raise ValueError("关联数据资产不存在")
    serialized = json.dumps(dataset.rows, sort_keys=True, ensure_ascii=False).encode()
    checksum = hashlib.sha256(serialized).hexdigest()
    natural_key = f"{analysis.id}:{checksum[:12]}:{datetime.now(timezone.utc).timestamp():.6f}"
    run = AnalysisRun(
        natural_key=natural_key,
        status="running",
        analysis_id=analysis.id,
        created_by=actor_id,
        checksum=checksum,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()
    try:
        result = run_algorithm(dataset.rows, analysis.config or {})
        run.result = result
        run.metrics = result.get("metrics", [])
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        analysis.status = "completed"
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.result = {"headline": "运行失败", "narrative": str(exc),
                      "metrics": [], "series": [], "table": [],
                      "method": "error", "caveat": "请检查数据字段与算法参数后重试。"}
        run.metrics = []
        run.completed_at = datetime.now(timezone.utc)
        analysis.status = "failed"
    return run


def list_comments(db: Session, run_id: str) -> list[Comment]:
    return list(db.scalars(select(Comment).where(Comment.run_id == run_id).order_by(Comment.created_at)))
"""
    files["src/controllers/auth_controller.py"] = """
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.schemas.auth import LoginRequest, TokenResponse, UserRead
from src.services.auth_service import authenticate


def login(db: Session, payload: LoginRequest) -> TokenResponse:
    result = authenticate(db, payload.email, payload.password)
    if not result:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    return TokenResponse(access_token=result[1])


def current_user(user) -> UserRead:
    return UserRead(id=user.id, email=user.email, display_name=user.display_name, role=user.role)
"""
    files["src/controllers/dataset_controller.py"] = """
from sqlalchemy.orm import Session

from src.models.workspace import Workspace
from src.schemas.dataset import DatasetCreate, DatasetList, DatasetRead
from src.services import audit_service, dataset_service


def list_items(db: Session) -> DatasetList:
    items = dataset_service.list_datasets(db)
    return DatasetList(items=[DatasetRead.model_validate(item) for item in items], total=len(items))


def create_item(db: Session, payload: DatasetCreate, user, workspace: Workspace) -> DatasetRead:
    item = dataset_service.create_dataset(
        db, workspace, user.id, payload.name, payload.source, payload.description, payload.rows
    )
    audit_service.record(db, "dataset.create", "dataset", item.id, user.id, {"rows": item.row_count})
    db.commit()
    db.refresh(item)
    return DatasetRead.model_validate(item)
"""
    files["src/controllers/analysis_controller.py"] = """
from sqlalchemy.orm import Session

from src.models.workspace import Workspace
from src.schemas.analysis import AnalysisCreate, AnalysisList, AnalysisRead
from src.services import analysis_service, audit_service


def list_items(db: Session) -> AnalysisList:
    items = analysis_service.list_analyses(db)
    return AnalysisList(items=[AnalysisRead.model_validate(item) for item in items], total=len(items))


def create_item(db: Session, payload: AnalysisCreate, user, workspace: Workspace) -> AnalysisRead:
    item = analysis_service.create_analysis(
        db, workspace, user.id, payload.name, payload.dataset_id, payload.kind,
        payload.hypothesis, payload.config
    )
    audit_service.record(db, "analysis.create", "analysis", item.id, user.id, {"kind": item.kind})
    db.commit()
    db.refresh(item)
    return AnalysisRead.model_validate(item)
"""
    files["src/controllers/run_controller.py"] = """
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.comment import Comment
from src.schemas.analysis_run import CommentCreate, RunList, RunRead
from src.schemas.comment import CommentRead
from src.services import analysis_service, audit_service, run_service


def list_items(db: Session) -> RunList:
    items = run_service.list_runs(db)
    return RunList(items=[RunRead.model_validate(item) for item in items], total=len(items))


def execute(db: Session, analysis_id: str, user) -> RunRead:
    analysis = analysis_service.get_analysis(db, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="分析方案不存在")
    try:
        item = run_service.execute_run(db, analysis, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit_service.record(db, "analysis.run", "analysis_run", item.id, user.id,
                         {"status": item.status, "checksum": item.checksum})
    db.commit()
    db.refresh(item)
    return RunRead.model_validate(item)


def get_item(db: Session, run_id: str) -> RunRead:
    item = run_service.get_run(db, run_id)
    if not item:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    return RunRead.model_validate(item)


def list_comments(db: Session, run_id: str) -> list[CommentRead]:
    return [CommentRead.model_validate(item) for item in run_service.list_comments(db, run_id)]


def create_comment(db: Session, run_id: str, payload: CommentCreate, user) -> CommentRead:
    run = run_service.get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    item = Comment(
        natural_key=f"{run_id}:{user.id}:{payload.body[:40]}:{len(run_id)}",
        body=payload.body,
        decision=payload.decision,
        run_id=run_id,
        author_id=user.id,
    )
    db.add(item)
    audit_service.record(db, "run.comment", "analysis_run", run_id, user.id,
                         {"decision": payload.decision})
    db.commit()
    db.refresh(item)
    return CommentRead.model_validate(item)
"""
    files["src/controllers/audit_controller.py"] = """
from sqlalchemy.orm import Session

from src.schemas.audit_log import AuditList, AuditRead
from src.services import audit_service


def list_items(db: Session) -> AuditList:
    items = audit_service.list_recent(db)
    return AuditList(items=[AuditRead.model_validate(item) for item in items], total=len(items))
"""
    files["src/routes/auth.py"] = """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.controllers import auth_controller
from src.database import get_db
from src.middlewares.auth import get_current_user
from src.schemas.auth import LoginRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return auth_controller.login(db, payload)


@router.get("/me", response_model=UserRead)
def me(user=Depends(get_current_user)):
    return auth_controller.current_user(user)
"""
    files["src/routes/datasets.py"] = """
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.controllers import dataset_controller
from src.database import get_db
from src.middlewares.auth import get_current_user, require_roles
from src.models.workspace import Workspace
from src.schemas.dataset import DatasetCreate, DatasetList, DatasetRead

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=DatasetList)
def index(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return dataset_controller.list_items(db)


@router.post("", response_model=DatasetRead)
def create(payload: DatasetCreate, db: Session = Depends(get_db),
           user=Depends(require_roles("admin", "analyst"))):
    workspace = db.scalar(select(Workspace))
    if not workspace:
        raise HTTPException(status_code=409, detail="工作区尚未初始化")
    return dataset_controller.create_item(db, payload, user, workspace)


@router.get("/{dataset_id}")
def detail(dataset_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from src.services.dataset_service import get_dataset
    item = get_dataset(db, dataset_id)
    if not item:
        raise HTTPException(status_code=404, detail="数据资产不存在")
    return DatasetRead.model_validate(item)
"""
    files["src/routes/analyses.py"] = """
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.controllers import analysis_controller
from src.database import get_db
from src.middlewares.auth import get_current_user, require_roles
from src.models.workspace import Workspace
from src.schemas.analysis import AnalysisCreate, AnalysisList, AnalysisRead

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.get("", response_model=AnalysisList)
def index(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return analysis_controller.list_items(db)


@router.post("", response_model=AnalysisRead)
def create(payload: AnalysisCreate, db: Session = Depends(get_db),
           user=Depends(require_roles("admin", "analyst"))):
    workspace = db.scalar(select(Workspace))
    if not workspace:
        raise HTTPException(status_code=409, detail="工作区尚未初始化")
    return analysis_controller.create_item(db, payload, user, workspace)


@router.get("/{analysis_id}", response_model=AnalysisRead)
def detail(analysis_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from src.services.analysis_service import get_analysis
    item = get_analysis(db, analysis_id)
    if not item:
        raise HTTPException(status_code=404, detail="分析方案不存在")
    return AnalysisRead.model_validate(item)
"""
    files["src/routes/runs.py"] = """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.controllers import run_controller
from src.database import get_db
from src.middlewares.auth import get_current_user, require_roles
from src.schemas.analysis_run import CommentCreate, RunList, RunRead
from src.schemas.comment import CommentRead

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=RunList)
def index(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return run_controller.list_items(db)


@router.get("/{run_id}", response_model=RunRead)
def detail(run_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return run_controller.get_item(db, run_id)


@router.get("/{run_id}/comments", response_model=list[CommentRead])
def comments(run_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return run_controller.list_comments(db, run_id)


@router.post("/{run_id}/comments", response_model=CommentRead)
def comment(run_id: str, payload: CommentCreate, db: Session = Depends(get_db),
            user=Depends(require_roles("admin", "reviewer"))):
    return run_controller.create_comment(db, run_id, payload, user)
"""
    files["src/routes/analysis_runs.py"] = """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.controllers import run_controller
from src.database import get_db
from src.middlewares.auth import require_roles
from src.schemas.analysis_run import RunRead

router = APIRouter(prefix="/analyses", tags=["analysis-runs"])


@router.post("/{analysis_id}/run", response_model=RunRead)
def execute(analysis_id: str, db: Session = Depends(get_db),
            user=Depends(require_roles("admin", "analyst"))):
    return run_controller.execute(db, analysis_id, user)
"""
    files["src/routes/audit.py"] = """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.controllers import audit_controller
from src.database import get_db
from src.middlewares.auth import get_current_user
from src.schemas.audit_log import AuditList

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditList)
def index(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return audit_controller.list_items(db)
"""
    files["src/routes/workspace.py"] = """
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.middlewares.auth import get_current_user
from src.models.workspace import Workspace
from src.schemas.workspace import WorkspaceRead

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("", response_model=WorkspaceRead)
def detail(db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.scalar(select(Workspace))
    if not item:
        raise HTTPException(status_code=404, detail="工作区尚未初始化")
    return WorkspaceRead.model_validate(item)
"""
    files["src/routes/health.py"] = """
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}
"""
    files["src/main.py"] = f"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database import Base, engine
from src.middlewares.errors import unhandled_error_handler
from src.middlewares.rate_limit import RateLimitMiddleware
from src.routes import analyses, analysis_runs, audit, auth, datasets, health, runs, workspace


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title={q(project["name"])}, lifespan=lifespan)
app.add_middleware(RateLimitMiddleware, limit=180, window_seconds=60)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(Exception, unhandled_error_handler)

for router in (health.router, auth.router, workspace.router, datasets.router,
               analyses.router, analysis_runs.router, runs.router, audit.router):
    app.include_router(router, prefix="/api")
"""
    files["src/worker/celery_app.py"] = f"""
from celery import Celery
from src.config import settings

celery_app = Celery("batch_worker", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    beat_schedule={{
        "write-heartbeat": {{
            "task": "src.worker.tasks.heartbeat",
            "schedule": 45.0,
        }}
    }},
)
celery_app.autodiscover_tasks(["src.worker"])
"""
    files["src/worker/tasks.py"] = f"""
from datetime import datetime, timezone
from pathlib import Path

from src.worker.celery_app import celery_app


@celery_app.task(name="src.worker.tasks.heartbeat")
def heartbeat():
    path = Path("/app/artifacts/worker-heartbeat.txt")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    return {{"project": {q(short)}, "status": "alive"}}
"""
    files["migrations/README.md"] = """
# Migrations

This batch uses `Base.metadata.create_all()` for deterministic first boot. A production
deployment should replace it with Alembic revisions before schema evolution.
"""
    return files


def seed_source(project: dict) -> str:
    entities = project["entities"]
    algorithms = project["algorithms"]
    return f'''
import argparse
import time

from sqlalchemy import select

from scripts.demo_data import demo_rows
from src.config import settings
from src.database import Base, SessionLocal, engine
from src.models.analysis import Analysis
from src.models.analysis_run import AnalysisRun
from src.models.audit_log import AuditLog
from src.models.comment import Comment
from src.models.dataset import Dataset
from src.models.user import User
from src.models.workspace import Workspace
from src.services.run_service import execute_run
from src.utils.security import hash_password


ACCOUNTS = [
    ("admin@batchdemo.dev", "演示管理员", "admin"),
    ("analyst@batchdemo.dev", "演示分析员", "analyst"),
    ("reviewer@batchdemo.dev", "演示复核员", "reviewer"),
]
PASSWORD = "Demo123!"


def wait_for_database(attempts=30):
    for index in range(attempts):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except Exception as exc:
            if index == attempts - 1:
                raise
            print(f"database not ready: {{exc}}", flush=True)
            time.sleep(2)


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        users = {{}}
        for email, display_name, role in ACCOUNTS:
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                user = User(email=email, display_name=display_name, role=role,
                            password_hash=hash_password(PASSWORD))
                db.add(user)
                db.flush()
            users[role] = user

        admin = users["admin"]
        analyst = users["analyst"]
        reviewer = users["reviewer"]
        workspace = db.scalar(select(Workspace).where(Workspace.natural_key == "demo-workspace"))
        if not workspace:
            workspace = Workspace(
                natural_key="demo-workspace",
                name={q(project["name"])},
                client_name={q(project["client"])},
                context_note={q(project["context"])},
                owner_id=admin.id,
            )
            db.add(workspace)
            db.flush()

        rows = demo_rows()
        chunk_size = max(len(rows) // 3, 1)
        datasets = []
        names = [
            {q(entities[0] + "基线")},
            {q(entities[0] + "复核样本")},
            {q(entities[0] + "历史快照")},
        ]
        sources = ["业务导出 CSV", "实验室复核 JSONL", "历史归档"]
        for index in range(3):
            subset = rows[index * chunk_size:(index + 1) * chunk_size] if index < 2 else rows[2 * chunk_size:]
            natural_key = f"demo-dataset-{{index}}"
            dataset = db.scalar(select(Dataset).where(Dataset.natural_key == natural_key))
            if not dataset:
                import hashlib
                import json
                raw = json.dumps(subset, sort_keys=True, ensure_ascii=False).encode()
                dataset = Dataset(
                    natural_key=natural_key,
                    name=names[index],
                    source=sources[index],
                    description=f"围绕{{workspace.name}}的{{names[index]}}，生成 seed 固定可复现。",
                    rows=subset,
                    row_count=len(subset),
                    checksum=hashlib.sha256(raw).hexdigest(),
                    workspace_id=workspace.id,
                    created_by=analyst.id,
                    status="ready",
                )
                db.add(dataset)
                db.flush()
            datasets.append(dataset)

        analyses = []
        definitions = [
            ({q(algorithms[0])}, "primary", {q("比较核心业务指标，并给出效应量与不确定性。")}),
            ({q(algorithms[1])}, "secondary", {q("用第二种口径复核主方案结论，检查敏感性与边界。")}),
            ({q(entities[2] + "稳健性方案")}, "primary", {q("按资产维度拆分，检查结论是否由单一分组驱动。")}),
            ({q(entities[4] + "复核方案")}, "secondary", {q("面向业务复核，保留算法口径与已知限制。")}),
        ]
        for index, (name, kind, hypothesis) in enumerate(definitions):
            natural_key = f"seed-analysis-{{index}}"
            item = db.scalar(select(Analysis).where(Analysis.natural_key == natural_key))
            if not item:
                item = Analysis(
                    natural_key=natural_key,
                    name=name,
                    kind=kind,
                    status="ready",
                    hypothesis=hypothesis,
                    config={{"seed": True, "variant": index + 1}},
                    dataset_id=datasets[0].id,
                    workspace_id=workspace.id,
                    created_by=analyst.id,
                )
                db.add(item)
                db.flush()
            analyses.append(item)

        runs = []
        for index, analysis in enumerate(analyses[:3]):
            natural_key = f"seed-run-{{index}}"
            run = db.scalar(select(AnalysisRun).where(AnalysisRun.natural_key == natural_key))
            if not run:
                run = execute_run(db, analysis, analyst.id)
                run.natural_key = natural_key
                db.flush()
            runs.append(run)

        if not db.scalar(select(Comment).where(Comment.natural_key == "seed-comment-0")):
            db.add(Comment(natural_key="seed-comment-0",
                           body="请补充样本分群后的敏感性说明。",
                           decision="changes_requested", run_id=runs[0].id,
                           author_id=reviewer.id))
        if not db.scalar(select(Comment).where(Comment.natural_key == "seed-comment-1")):
            db.add(Comment(natural_key="seed-comment-1",
                           body="主口径已复核，可在周会发布。",
                           decision="approved", run_id=runs[1].id,
                           author_id=reviewer.id))
        if not db.scalar(select(AuditLog).where(AuditLog.action == "seed.bootstrap")):
            db.add(AuditLog(action="seed.bootstrap", resource_type="workspace",
                            resource_id=workspace.id, actor_id=admin.id,
                            detail={{"datasets": len(datasets), "analyses": len(analyses),
                                     "project": {q(project["short"])}}}))
        db.commit()
        print(f"seed complete: users=3 datasets={{len(datasets)}} analyses={{len(analyses)}} runs={{len(runs)}}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()
    if args.wait:
        wait_for_database()
    seed()


if __name__ == "__main__":
    main()
'''


def readme_source(project: dict) -> str:
    fe, be, db_port = ports(project)
    return f"""
# {project['name']}

{project['client']}的数据分析工作台。{project['context']}

## 真实场景

- 当前工作流：{project['workflow']}
- 痛点：{'；'.join(project['pains'])}。
- 上游：业务导出、实验室复核或历史归档数据。
- 本系统：统一资产登记、分析编排、Python 计算、结果复核与审计。
- 下游：业务负责人、数据管理员与复核员在周会/评审中使用结果。

## 功能

- {project['pages'][0]}：核心指标、数据状态与近期运行。
- {project['pages'][1]}：资产列表、样本量与校验摘要。
- {project['pages'][2]}：从资产创建分析方案并触发运行。
- {project['pages'][3]}：查看真实 Python 计算结果、方法、限制与表格。
- {project['pages'][4]}：审计日志、复核意见与角色权限追踪。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec backend python -m scripts.seed_demo
```

访问：

- 前端：http://localhost:{fe}
- 后端接口：http://localhost:{be}/api/health
- 数据库映射：localhost:{db_port}

## 演示账号

| 角色 | 邮箱 | 密码 | 权限 |
|---|---|---|---|
| 数据管理员 | admin@batchdemo.dev | Demo123! | 全部页面、创建与运行 |
| 分析员 | analyst@batchdemo.dev | Demo123! | 创建资产、方案与运行 |
| 业务复核员 | reviewer@batchdemo.dev | Demo123! | 只读结果、提交复核意见 |

## 技术栈

| 服务 | 技术 |
|---|---|
| frontend | {project['frontend']} + TypeScript + Vite + Nginx |
| backend | Python 3.11 + FastAPI + SQLAlchemy |
| worker | Celery + Redis |
| db | {project['db']} |
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

{project['algorithms'][0]}：后端按输入样本真实计算并返回效应、区间或评分。

{project['algorithms'][1]}：作为第二层诊断；结果、方法和限制同时返回，前端不硬编码图形数据。

## License

MIT
"""


def frontend_common(project: dict) -> dict[str, str]:
    fonts = project["fonts"]
    font_query = "&".join(
        f"family={font.replace(' ', '+')}:wght@400;500;600;700" for font in fonts
    )
    hue = (project["n"] * 37 + 18) % 360
    accent_hue = (hue + 42) % 360
    secondary_hue = (hue + 138) % 360
    css = f"""
@import url('https://fonts.googleapis.com/css2?{font_query}&display=swap');

:root {{
  --bg: oklch(17% 0.018 {hue});
  --surface: oklch(23% 0.022 {hue});
  --surface-raised: oklch(27% 0.026 {hue});
  --paper: oklch(92% 0.018 {hue});
  --ink: oklch(91% 0.015 {hue});
  --muted: oklch(71% 0.018 {hue});
  --line: oklch(42% 0.025 {hue} / 0.55);
  --accent: oklch(66% 0.14 {accent_hue});
  --accent-soft: oklch(66% 0.14 {accent_hue} / 0.15);
  --secondary: oklch(66% 0.09 {secondary_hue});
  --danger: oklch(62% 0.17 27);
  --warning: oklch(75% 0.13 78);
  --font-display: "{fonts[0]}", serif;
  --font-mono: "{fonts[1]}", monospace;
  --sidebar: 248px;
}}

* {{ box-sizing: border-box; }}
html, body, #app, #root {{ min-height: 100%; }}
body {{
  margin: 0;
  color: var(--ink);
  background:
    linear-gradient(115deg, oklch(20% 0.02 {hue} / .84), transparent 58%),
    var(--bg);
  font-family: var(--font-display);
}}
button, input, select, textarea {{ font: inherit; }}
a {{ color: inherit; text-decoration: none; }}
.mono {{ font-family: var(--font-mono); letter-spacing: -.02em; }}
.muted {{ color: var(--muted); }}
.eyebrow {{
  text-transform: uppercase;
  letter-spacing: .14em;
  font-size: 11px;
  color: var(--accent);
  font-family: var(--font-mono);
}}
h1, h2, h3, p {{ margin-top: 0; }}
h1 {{ font-size: clamp(34px, 4vw, 62px); line-height: .98; letter-spacing: -.035em; }}
h2 {{ font-size: clamp(22px, 2vw, 32px); line-height: 1.05; }}
h3 {{ font-size: 16px; }}

.login-shell {{
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(360px, 1.25fr) minmax(330px, .75fr);
  padding: 5vw;
  gap: 5vw;
  align-items: end;
}}
.login-thesis {{ align-self: stretch; display: flex; flex-direction: column; justify-content: space-between; }}
.login-thesis h1 {{ max-width: 760px; margin-bottom: 24px; }}
.login-meta {{ display: flex; gap: 24px; color: var(--muted); font-size: 13px; flex-wrap: wrap; }}
.login-form {{
  border-left: 1px solid var(--line);
  padding: 28px 0 28px 32px;
}}
.login-form label {{ display: grid; gap: 8px; margin: 18px 0; color: var(--muted); font-size: 13px; }}
.login-form input {{
  width: 100%; background: transparent; color: var(--ink); border: 0;
  border-bottom: 1px solid var(--line); padding: 12px 2px; outline: none;
}}
.login-form input:focus {{ border-color: var(--accent); }}

.app-shell {{ min-height: 100vh; display: grid; grid-template-columns: var(--sidebar) minmax(0, 1fr); }}
.sidebar {{
  position: sticky; top: 0; height: 100vh; padding: 28px 22px;
  border-right: 1px solid var(--line); background: oklch(15% 0.018 {hue} / .78);
  display: flex; flex-direction: column; gap: 28px; z-index: 5;
}}
.brand {{ display: flex; gap: 12px; align-items: center; }}
.brand-mark {{
  width: 38px; height: 38px; border: 1px solid var(--accent);
  display: grid; place-items: center; font-family: var(--font-mono); color: var(--accent);
}}
.brand strong {{ display: block; font-size: 15px; letter-spacing: .02em; }}
.brand small {{ color: var(--muted); font-size: 10px; }}
.nav-list {{ display: grid; gap: 5px; }}
.nav-link {{
  display: flex; align-items: center; gap: 10px; padding: 10px 11px;
  border-left: 2px solid transparent; color: var(--muted); font-size: 13px;
  transition: transform .28s cubic-bezier(.16,1,.3,1), color .2s;
}}
.nav-link:hover {{ transform: translateX(4px); color: var(--ink); }}
.nav-link.active {{ color: var(--ink); border-color: var(--accent); background: var(--accent-soft); }}
.sidebar-foot {{ margin-top: auto; display: grid; gap: 14px; }}
.user-line {{ display: flex; justify-content: space-between; gap: 12px; font-size: 12px; }}
.main-stage {{ min-width: 0; padding: 32px clamp(22px, 4vw, 64px) 64px; }}
.page-head {{
  display: flex; align-items: flex-end; justify-content: space-between; gap: 24px;
  margin-bottom: 34px; padding-bottom: 18px; border-bottom: 1px solid var(--line);
}}
.page-head p {{ max-width: 680px; margin-bottom: 0; color: var(--muted); line-height: 1.7; }}
.page-head h1 {{ margin-bottom: 8px; }}
.content-grid {{ display: grid; gap: 22px; }}
.grid-2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
.grid-3 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
.grid-main {{ grid-template-columns: minmax(0, 1.45fr) minmax(280px, .55fr); }}
.panel {{ border-top: 1px solid var(--line); padding-top: 18px; min-width: 0; }}
.panel-head {{ display: flex; justify-content: space-between; gap: 16px; align-items: baseline; margin-bottom: 16px; }}
.stat-row {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-top: 1px solid var(--line); }}
.stat {{ padding: 20px 14px 16px 0; border-right: 1px solid var(--line); }}
.stat:last-child {{ border-right: 0; }}
.stat-row-compact {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
.stat-row-compact .stat-value {{ font-size: clamp(24px, 2vw, 34px); }}
.stat-row-compact .mono {{ overflow-wrap: anywhere; font-size: 11px; }}
.stat-label {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .12em; }}
.stat-value {{ margin-top: 10px; font-size: clamp(26px, 3vw, 46px); font-family: var(--font-mono); }}
.positive {{ color: var(--secondary); }}
.negative {{ color: var(--danger); }}
.neutral {{ color: var(--ink); }}
.button {{
  border: 1px solid var(--line); color: var(--ink); background: transparent;
  min-height: 38px; padding: 9px 14px; cursor: pointer; display: inline-flex;
  align-items: center; justify-content: center; gap: 8px;
  transition: transform .22s cubic-bezier(.16,1,.3,1), border-color .2s;
}}
.button:hover {{ transform: translateY(-2px); border-color: var(--accent); }}
.button.primary {{ background: var(--accent); color: oklch(18% 0.02 {hue}); border-color: var(--accent); }}
.button:disabled {{ opacity: .45; cursor: not-allowed; transform: none; }}
.table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
.table th {{ text-align: left; color: var(--muted); font-weight: 500; padding: 10px 8px; border-bottom: 1px solid var(--line); }}
.table td {{ padding: 13px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }}
.status {{ display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; }}
.status::before {{ content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; }}
.bar-list {{ display: grid; gap: 12px; }}
.bar-row {{ display: grid; grid-template-columns: minmax(90px, 180px) 1fr 74px; gap: 12px; align-items: center; font-size: 12px; }}
.bar-track {{ height: 6px; background: var(--line); overflow: hidden; }}
.bar-fill {{ height: 100%; background: var(--accent); transform-origin: left; animation: grow .7s cubic-bezier(.16,1,.3,1) both; }}
@keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
.empty {{
  min-height: 220px; display: grid; place-items: center; text-align: center;
  border: 1px dashed var(--line); color: var(--muted); padding: 30px;
}}
.error-box {{ border-left: 2px solid var(--danger); padding: 14px 18px; background: oklch(30% .04 27 / .16); }}
.form-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
.field {{ display: grid; gap: 8px; }}
.field label {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .1em; }}
.field input, .field select, .field textarea {{
  background: var(--surface); color: var(--ink); border: 1px solid var(--line);
  min-height: 40px; padding: 9px 11px; outline: none;
}}
.field textarea {{ min-height: 96px; resize: vertical; }}
.run-headline {{ font-size: clamp(28px, 4.2vw, 58px); line-height: 1.04; max-width: 900px; }}
.method-tag {{ display: inline-block; font-family: var(--font-mono); font-size: 11px; padding: 4px 7px; border: 1px solid var(--line); }}
.caveat {{ border-left: 2px solid var(--warning); padding-left: 14px; color: var(--muted); line-height: 1.7; }}
.audit-row {{ display: grid; grid-template-columns: 150px 180px 1fr; gap: 16px; padding: 13px 0; border-bottom: 1px solid var(--line); font-size: 12px; }}
.tabs {{ display: flex; gap: 16px; border-bottom: 1px solid var(--line); margin-bottom: 22px; }}
.tab {{ padding: 10px 0; color: var(--muted); border-bottom: 2px solid transparent; }}
.tab.active {{ color: var(--ink); border-color: var(--accent); }}

/* Nine deliberately different spatial systems share the same accessible components. */
.layout-blueprint body, body.layout-blueprint {{
  background-image: linear-gradient(var(--line) 1px, transparent 1px), linear-gradient(90deg, var(--line) 1px, transparent 1px);
  background-size: 42px 42px;
}}
.layout-blueprint .main-stage {{ padding-left: clamp(40px, 7vw, 110px); }}
.layout-blueprint .panel {{ border-top-width: 2px; border-top-style: dashed; }}
.layout-journal .main-stage {{ max-width: 1320px; margin: 0 auto; }}
.layout-journal .page-head {{ display: block; }}
.layout-journal .panel {{ border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); padding: 22px 0; }}
.layout-archive .sidebar {{ border-right-style: dashed; }}
.layout-archive .stat {{ padding-left: 16px; }}
.layout-swatch .stat:nth-child(2n) {{ background: var(--accent-soft); }}
.layout-swatch .panel-head {{ border-left: 10px solid var(--accent); padding-left: 12px; }}
.layout-atlas .main-stage {{
  background-image: linear-gradient(30deg, var(--line) 1px, transparent 1px);
  background-size: 72px 72px;
}}
.layout-atlas .page-head {{ align-items: center; }}
.layout-radar .sidebar {{ background: oklch(13% .02 {accent_hue}); }}
.layout-radar .stat-value {{ text-shadow: 0 0 18px var(--accent-soft); }}
.layout-control .main-stage {{ padding-top: 22px; }}
.layout-control .page-head {{ border-bottom: 3px double var(--line); }}
.layout-control .grid-3 {{ gap: 1px; background: var(--line); }}
.layout-control .grid-3 > * {{ background: var(--bg); }}
.layout-registry .main-stage {{ max-width: 1180px; margin: auto; }}
.layout-registry .page-head {{ text-align: center; display: block; }}
.layout-registry .table th {{ text-transform: uppercase; letter-spacing: .12em; }}

@media (max-width: 1024px) {{
  .app-shell {{ grid-template-columns: 84px minmax(0, 1fr); }}
  .sidebar {{ padding: 22px 12px; }}
  .brand text, .brand strong, .brand small, .nav-link span, .sidebar-foot .user-line {{ display: none; }}
  .nav-link {{ justify-content: center; padding: 12px 5px; }}
  .grid-3 {{ grid-template-columns: 1fr 1fr; }}
  .grid-main {{ grid-template-columns: 1fr; }}
}}
@media (max-width: 720px) {{
  .login-shell {{ grid-template-columns: 1fr; padding: 28px; align-items: start; }}
  .login-form {{ border-left: 0; border-top: 1px solid var(--line); padding: 24px 0 0; }}
  .app-shell {{ display: block; }}
  .sidebar {{
    position: static; height: auto; flex-direction: row; overflow-x: auto;
    align-items: center; border-right: 0; border-bottom: 1px solid var(--line);
  }}
  .brand {{ min-width: 44px; }}
  .nav-list {{ display: flex; }}
  .sidebar-foot {{ margin: 0 0 0 auto; }}
  .main-stage {{ padding: 24px 18px 48px; }}
  .page-head {{ display: block; }}
  .grid-2, .grid-3, .form-grid, .stat-row {{ grid-template-columns: 1fr; }}
  .stat {{ border-right: 0; border-bottom: 1px solid var(--line); }}
  .audit-row {{ grid-template-columns: 1fr; gap: 5px; }}
  .bar-row {{ grid-template-columns: 110px 1fr 60px; }}
}}
"""
    domain = f"""
export const PROJECT_NAME = {q(project['name'])};
export const CLIENT_NAME = {q(project['client'])};
export const ENTITY_LABELS = {json.dumps(project['entities'], ensure_ascii=False, indent=2)} as const;
export const PAGE_LABELS = {json.dumps(project['pages'], ensure_ascii=False, indent=2)} as const;
export const ALGORITHM_LABELS = {json.dumps(project['algorithms'], ensure_ascii=False, indent=2)} as const;
"""
    return {"src/styles.css": css, "src/constants/domain.ts": domain}


def react_frontend(project: dict) -> dict[str, str]:
    files = frontend_common(project)
    files.update(
        {
            "package.json": """
{
  "name": "analytics-workbench",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {"dev": "vite --host 0.0.0.0", "build": "tsc -b && vite build", "preview": "vite preview"},
  "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1", "react-router-dom": "^6.28.0"},
  "devDependencies": {"@types/react": "^18.3.12", "@types/react-dom": "^18.3.1", "@vitejs/plugin-react": "^4.3.4", "typescript": "^5.7.2", "vite": "^6.0.3"}
}
""",
            "tsconfig.json": """
{"compilerOptions":{"target":"ES2022","useDefineForClassFields":true,"lib":["ES2022","DOM","DOM.Iterable"],"allowJs":false,"skipLibCheck":true,"esModuleInterop":true,"allowSyntheticDefaultImports":true,"strict":true,"forceConsistentCasingInFileNames":true,"module":"ESNext","moduleResolution":"Bundler","resolveJsonModule":true,"isolatedModules":true,"noEmit":true,"jsx":"react-jsx"},"include":["src"],"references":[]}
""",
            "vite.config.ts": """
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({ plugins: [react()], server: { port: 5173 } });
""",
            "index.html": f"""
<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>{project['name']}</title></head><body class="layout-{project['layout']}"><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>
""",
            "Dockerfile": """
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
""",
            "nginx.conf": """
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;
  location = /healthz { return 200 "ok\\n"; add_header Content-Type text/plain; }
  location /api/ { proxy_pass http://backend:8000; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; }
  location / { try_files $uri /index.html; }
}
""",
            "src/main.tsx": """
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";
ReactDOM.createRoot(document.getElementById("root")!).render(<React.StrictMode><BrowserRouter><App/></BrowserRouter></React.StrictMode>);
""",
            "src/App.tsx": """
import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./layouts/AppShell";
import AnalysesPage from "./pages/AnalysesPage";
import DatasetsPage from "./pages/DatasetsPage";
import GovernancePage from "./pages/GovernancePage";
import LoginPage from "./pages/LoginPage";
import OverviewPage from "./pages/OverviewPage";
import RunDetailPage from "./pages/RunDetailPage";
import { getToken } from "./api/client";

function Protected() {
  return getToken() ? <AppShell/> : <Navigate to="/login" replace/>;
}

export default function App() {
  return <Routes>
    <Route path="/login" element={<LoginPage/>}/>
    <Route element={<Protected/>}>
      <Route path="/overview" element={<OverviewPage/>}/>
      <Route path="/datasets" element={<DatasetsPage/>}/>
      <Route path="/analyses" element={<AnalysesPage/>}/>
      <Route path="/runs/:runId" element={<RunDetailPage/>}/>
      <Route path="/governance" element={<GovernancePage/>}/>
    </Route>
    <Route path="*" element={<Navigate to="/overview" replace/>}/>
  </Routes>;
}
""",
            "src/types/index.ts": """
export type Role = "admin" | "analyst" | "reviewer";
export interface User { id:string; email:string; display_name:string; role:Role }
export interface Workspace { id:string; name:string; client_name:string; context_note:string; }
export interface Dataset { id:string; name:string; source:string; status:string; row_count:number; checksum:string; description:string; workspace_id:string; created_by:string; }
export interface Analysis { id:string; name:string; kind:string; status:string; hypothesis:string; config:Record<string,unknown>; dataset_id:string; workspace_id:string; created_by:string; }
export interface Metric { label:string; value:number|string; unit?:string; tone?:string; }
export interface Series { label:string; value:number; }
export interface RunResult { headline:string; narrative:string; metrics:Metric[]; series:Series[]; table:Record<string,unknown>[]; method:string; caveat:string; }
export interface Run { id:string; status:string; result:RunResult; metrics:Metric[]; error_message:string; checksum:string; analysis_id:string; created_at:string; }
export interface Audit { id:string; action:string; resource_type:string; resource_id:string; actor_id:string; detail:Record<string,unknown>; created_at:string; }
export interface Comment { id:string; body:string; decision:string; run_id:string; author_id:string; created_at:string; }
export interface ListResponse<T> { items:T[]; total:number; }
""",
            "src/constants/enums.ts": """
export const ROLES = { admin: "数据管理员", analyst: "分析员", reviewer: "业务复核员" } as const;
export const STATUS_LABELS: Record<string,string> = { draft:"草稿", ready:"就绪", running:"运行中", completed:"已完成", failed:"失败" };
export const NAV_ITEMS = [
  { path:"/overview", icon:"01", label:"总览" },
  { path:"/datasets", icon:"02", label:"资产" },
  { path:"/analyses", icon:"03", label:"编排" },
  { path:"/governance", icon:"04", label:"治理" },
] as const;
""",
            "src/api/client.ts": """
const TOKEN_KEY = "analytics_token";
export function getToken(){ return localStorage.getItem(TOKEN_KEY); }
export function setToken(token:string){ localStorage.setItem(TOKEN_KEY, token); }
export function clearToken(){ localStorage.removeItem(TOKEN_KEY); }
export async function api<T>(path:string, init:RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`/api${path}`, {...init, headers});
  if (!response.ok) {
    const payload = await response.json().catch(() => ({detail:"请求失败"}));
    throw new Error(payload.detail || "请求失败");
  }
  return response.json();
}
""",
            "src/api/auth.ts": """
import { api } from "./client";
import type { User } from "../types";
export async function login(email:string,password:string){ return api<{access_token:string}>("/auth/login",{method:"POST",body:JSON.stringify({email,password})}); }
export function me(){ return api<User>("/auth/me"); }
""",
            "src/api/workspace.ts": """
import { api } from "./client";
import type { Workspace } from "../types";
export const getWorkspace = () => api<Workspace>("/workspace");
""",
            "src/api/datasets.ts": """
import { api } from "./client";
import type { Dataset, ListResponse } from "../types";
export const listDatasets = () => api<ListResponse<Dataset>>("/datasets");
export const createDataset = (payload:{name:string;description:string;rows:Record<string,unknown>[]}) => api<Dataset>("/datasets",{method:"POST",body:JSON.stringify(payload)});
""",
            "src/api/analyses.ts": """
import { api } from "./client";
import type { Analysis, ListResponse, Run } from "../types";
export const listAnalyses = () => api<ListResponse<Analysis>>("/analyses");
export const createAnalysis = (payload:{name:string;dataset_id:string;kind:string;hypothesis:string;config:Record<string,unknown>}) => api<Analysis>("/analyses",{method:"POST",body:JSON.stringify(payload)});
export const executeAnalysis = (id:string) => api<Run>(`/analyses/${id}/run`,{method:"POST"});
""",
            "src/api/runs.ts": """
import { api } from "./client";
import type { Comment, ListResponse, Run } from "../types";
export const listRuns = () => api<ListResponse<Run>>("/runs");
export const getRun = (id:string) => api<Run>(`/runs/${id}`);
export const listComments = (id:string) => api<Comment[]>(`/runs/${id}/comments`);
export const addComment = (id:string,body:string,decision="pending") => api<Comment>(`/runs/${id}/comments`,{method:"POST",body:JSON.stringify({body,decision})});
""",
            "src/api/audit.ts": """
import { api } from "./client";
import type { Audit, ListResponse } from "../types";
export const listAudit = () => api<ListResponse<Audit>>("/audit");
""",
            "src/stores/auth.ts": """
import { me } from "../api/auth";
import type { User } from "../types";
export async function loadUser(): Promise<User> { return me(); }
""",
            "src/hooks/useAsync.ts": """
import { useCallback, useEffect, useState } from "react";
export function useAsync<T>(loader:()=>Promise<T>, deps:unknown[] = []) {
  const [data,setData] = useState<T|null>(null);
  const [error,setError] = useState("");
  const [loading,setLoading] = useState(true);
  const reload = useCallback(()=>{
    setLoading(true); setError("");
    loader().then(setData).catch((e)=>setError(e.message)).finally(()=>setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },deps);
  useEffect(reload,[reload]);
  return {data,error,loading,reload};
}
""",
            "src/hooks/useAuth.ts": """
import { useEffect, useState } from "react";
import { loadUser } from "../stores/auth";
import type { User } from "../types";
export function useAuth(){ const [user,setUser]=useState<User|null>(null); useEffect(()=>{loadUser().then(setUser).catch(()=>undefined)},[]); return user; }
""",
            "src/utils/format.ts": """
export const number = (value:number|string) => typeof value === "number" ? new Intl.NumberFormat("zh-CN",{maximumFractionDigits:3}).format(value) : value;
export const dateTime = (value:string) => value ? new Intl.DateTimeFormat("zh-CN",{dateStyle:"medium",timeStyle:"short"}).format(new Date(value)) : "—";
export const checksum = (value:string) => value ? `${value.slice(0,8)}…${value.slice(-4)}` : "—";
""",
            "src/utils/tone.ts": """
export const toneClass = (tone?:string) => tone === "positive" ? "positive" : tone === "negative" ? "negative" : "neutral";
""",
            "src/components/common/Button.tsx": """
import type { ButtonHTMLAttributes } from "react";
export default function Button({primary=false,className="",...props}:ButtonHTMLAttributes<HTMLButtonElement>&{primary?:boolean}){ return <button className={`button ${primary?"primary":""} ${className}`} {...props}/>; }
""",
            "src/components/common/Panel.tsx": """
import type { ReactNode } from "react";
export default function Panel({title,action,children}:{title:string;action?:ReactNode;children:ReactNode}){ return <section className="panel"><div className="panel-head"><h3>{title}</h3>{action}</div>{children}</section>; }
""",
            "src/components/common/Stat.tsx": """
import { toneClass } from "../../utils/tone";
import { number } from "../../utils/format";
export default function Stat({label,value,unit="",tone="neutral"}:{label:string;value:number|string;unit?:string;tone?:string}){ return <div className="stat"><div className="stat-label">{label}</div><div className={`stat-value ${toneClass(tone)}`}>{number(value)}<small>{unit && <span className="muted"> {unit}</span>}</small></div></div>; }
""",
            "src/components/common/StatusBadge.tsx": """
import { STATUS_LABELS } from "../../constants/enums";
export default function StatusBadge({status}:{status:string}){ const positive=["ready","completed"].includes(status); const negative=status==="failed"; return <span className={`status ${negative?"negative":positive?"positive":"neutral"}`}>{STATUS_LABELS[status]||status}</span>; }
""",
            "src/components/common/BarChart.tsx": """
import type { Series } from "../../types";
import { number } from "../../utils/format";
export default function BarChart({series}:{series:Series[]}){ if(!series.length) return <div className="empty">当前结果没有可绘制的序列。</div>; const max=Math.max(...series.map(item=>Math.abs(item.value)),1); return <div className="bar-list">{series.map(item=><div className="bar-row" key={item.label}><span title={item.label}>{item.label}</span><div className="bar-track"><div className="bar-fill" style={{width:`${Math.max(Math.abs(item.value)/max*100,3)}%`}}/></div><span className="mono">{number(item.value)}</span></div>)}</div>; }
""",
            "src/components/common/DataTable.tsx": """
export default function DataTable({rows}:{rows:Record<string,unknown>[]}){ if(!rows.length) return <div className="empty">暂无明细。检查数据字段后重新运行。</div>; const columns=Array.from(new Set(rows.flatMap(Object.keys))).slice(0,8); return <div style={{overflowX:"auto"}}><table className="table"><thead><tr>{columns.map(column=><th key={column}>{column}</th>)}</tr></thead><tbody>{rows.slice(0,20).map((row,index)=><tr key={index}>{columns.map(column=><td key={column}>{typeof row[column]==="object"?JSON.stringify(row[column]):String(row[column]??"—")}</td>)}</tr>)}</tbody></table></div>; }
""",
            "src/layouts/AppShell.tsx": """
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { clearToken } from "../api/client";
import { ROLES, NAV_ITEMS } from "../constants/enums";
import { CLIENT_NAME, ENTITY_LABELS, PROJECT_NAME } from "../constants/domain";
import { useAuth } from "../hooks/useAuth";
export default function AppShell(){ const user=useAuth(); const navigate=useNavigate(); const location=useLocation(); return <div className="app-shell"><aside className="sidebar"><div className="brand"><div className="brand-mark">Δ</div><div><strong>{PROJECT_NAME}</strong><small>{CLIENT_NAME}</small></div></div><nav className="nav-list">{NAV_ITEMS.map(item=><NavLink className={({isActive})=>`nav-link ${isActive?"active":""}`} to={item.path} key={item.path}><b className="mono">{item.icon}</b><span>{item.label}</span></NavLink>)}</nav><div className="sidebar-foot"><div className="user-line"><span>{user?.display_name||"读取中"}</span><span className="mono">{user?ROLES[user.role]:"—"}</span></div><button className="button" onClick={()=>{clearToken();navigate("/login")}}>退出登录</button></div></aside><main className="main-stage"><Outlet/></main></div>; }
""",
            "src/pages/LoginPage.tsx": """
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api/auth";
import { setToken } from "../api/client";
import Button from "../components/common/Button";
import { ALGORITHM_LABELS, CLIENT_NAME, ENTITY_LABELS, PROJECT_NAME } from "../constants/domain";
export default function LoginPage(){ const [email,setEmail]=useState("analyst@batchdemo.dev"); const [password,setPassword]=useState("Demo123!"); const [error,setError]=useState(""); const [loading,setLoading]=useState(false); const navigate=useNavigate(); async function submit(event:FormEvent){event.preventDefault();setLoading(true);setError("");try{const result=await login(email,password);setToken(result.access_token);navigate("/overview")}catch(e){setError((e as Error).message)}finally{setLoading(false)}} return <main className="login-shell"><section className="login-thesis"><div><div className="eyebrow">Evidence-first analytics workspace</div><h1>{PROJECT_NAME}<br/><span className="muted">让每次判读都能回到数据。</span></h1><p className="muted" style={{maxWidth:620,lineHeight:1.8}}>{CLIENT_NAME} · {ENTITY_LABELS[0]} / {ENTITY_LABELS[2]} / {ENTITY_LABELS[4]}</p></div><div className="login-meta"><span>{ALGORITHM_LABELS[0]}</span><span>{ALGORITHM_LABELS[1]}</span><span>审计可追溯</span></div></section><form className="login-form" onSubmit={submit}><div className="eyebrow">进入工作区</div><h2>三角色演示</h2>{error&&<div className="error-box">{error}</div>}<label>邮箱<input value={email} onChange={e=>setEmail(e.target.value)} type="email" autoComplete="username"/></label><label>密码<input value={password} onChange={e=>setPassword(e.target.value)} type="password" autoComplete="current-password"/></label><Button primary type="submit" disabled={loading}>{loading?"验证中…":"登录"}</Button><p className="muted" style={{fontSize:11,marginTop:20}}>analyst@batchdemo.dev / reviewer@batchdemo.dev / admin@batchdemo.dev · Demo123!</p></form></main>; }
""",
            "src/pages/OverviewPage.tsx": """
import { Link } from "react-router-dom";
import { listDatasets } from "../api/datasets";
import { listRuns } from "../api/runs";
import { getWorkspace } from "../api/workspace";
import BarChart from "../components/common/BarChart";
import Panel from "../components/common/Panel";
import Stat from "../components/common/Stat";
import StatusBadge from "../components/common/StatusBadge";
import { ENTITY_LABELS, PAGE_LABELS } from "../constants/domain";
import { useAsync } from "../hooks/useAsync";
import { checksum, dateTime } from "../utils/format";
export default function OverviewPage(){ const workspace=useAsync(getWorkspace); const datasets=useAsync(listDatasets); const runs=useAsync(listRuns); const latest=runs.data?.items[0]; return <><header className="page-head"><div><div className="eyebrow">{PAGE_LABELS[0]}</div><h1>今天要判读什么？</h1><p>{workspace.data?.context_note||"正在读取工作区背景…"}</p></div><Link className="button primary" to="/analyses">创建分析</Link></header><div className="stat-row"><Stat label={ENTITY_LABELS[1]} value={datasets.data?.total||0} unit="份"/><Stat label="分析方案" value={runs.data?.total||0} unit="次运行"/><Stat label="最近状态" value={latest?.status==="completed"?"就绪":"待运行"} tone={latest?.status==="completed"?"positive":"neutral"}/><Stat label="数据校验" value={datasets.data?.items[0]?checksum(datasets.data.items[0].checksum):"—"}/></div><div className="content-grid grid-main" style={{marginTop:32}}><Panel title="最近运行序列" action={latest&&<StatusBadge status={latest.status}/>}>{latest?.result?.series?.length?<BarChart series={latest.result.series.slice(0,8)}/>:<div className="empty"><div><h3>首条结果尚未生成</h3><p>从分析编排选择资产并运行。</p></div></div>}</Panel><Panel title="操作提示"><div className="content-grid"><div><div className="eyebrow">01 / 资产</div><p>{datasets.data?.items[0]?.name||"等待资产加载"}</p></div><div><div className="eyebrow">02 / 计算</div><p>所有指标由 Python 后端计算，前端只渲染返回结果。</p></div><div><div className="eyebrow">03 / 复核</div><p>最近更新时间：{latest?dateTime(latest.created_at):"—"}</p></div></div></Panel></div></>; }
""",
            "src/pages/DatasetsPage.tsx": """
import { listDatasets } from "../api/datasets";
import DataTable from "../components/common/DataTable";
import Panel from "../components/common/Panel";
import StatusBadge from "../components/common/StatusBadge";
import { ENTITY_LABELS, PAGE_LABELS } from "../constants/domain";
import { useAsync } from "../hooks/useAsync";
import { checksum } from "../utils/format";
export default function DatasetsPage(){ const {data,error}=useAsync(listDatasets); return <><header className="page-head"><div><div className="eyebrow">{PAGE_LABELS[1]}</div><h1>{ENTITY_LABELS[1]}</h1><p>列出可用样本、来源、行数与内容校验，确保每次运行都能定位输入版本。</p></div><span className="method-tag">{data?.total||0} 份资产</span></header>{error&&<div className="error-box">{error}</div>}<div className="grid-3 content-grid">{data?.items.map(item=><Panel key={item.id} title={item.name} action={<StatusBadge status={item.status}/>}><div className="eyebrow">{item.source}</div><p className="muted">{item.description}</p><div className="stat-row"><div className="stat"><div className="stat-label">样本</div><div className="stat-value">{item.row_count.toLocaleString()}</div></div><div className="stat"><div className="stat-label">校验</div><div className="mono" style={{marginTop:12}}>{checksum(item.checksum)}</div></div></div></Panel>)}</div><div style={{marginTop:34}}><Panel title="字段抽样"><DataTable rows={[{name:"content_checksum",value:data?.items[0]?.checksum||"—"},{name:"role_scope",value:"admin / analyst / reviewer"},{name:"storage",value:"database JSON snapshot"}]}/></Panel></div></>; }
""",
            "src/pages/AnalysesPage.tsx": """
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createAnalysis, executeAnalysis, listAnalyses } from "../api/analyses";
import { listDatasets } from "../api/datasets";
import Button from "../components/common/Button";
import Panel from "../components/common/Panel";
import StatusBadge from "../components/common/StatusBadge";
import { ALGORITHM_LABELS, ENTITY_LABELS, PAGE_LABELS } from "../constants/domain";
import { useAsync } from "../hooks/useAsync";
export default function AnalysesPage(){ const analyses=useAsync(listAnalyses); const datasets=useAsync(listDatasets); const [name,setName]=useState(`${ALGORITHM_LABELS[0]} ${new Date().toLocaleDateString("zh-CN")}`); const [datasetId,setDatasetId]=useState(""); const [hypothesis,setHypothesis]=useState("检查主指标差异是否可以由抽样波动解释。"); const [busy,setBusy]=useState(""); const [error,setError]=useState(""); const navigate=useNavigate(); const selected=datasetId||datasets.data?.items[0]?.id||""; async function create(event:FormEvent){event.preventDefault();setBusy("create");setError("");try{const item=await createAnalysis({name,dataset_id:selected,kind:"primary",hypothesis,config:{clusters:3,topics:4,min_samples:5}});analyses.reload()}catch(e){setError((e as Error).message)}finally{setBusy("")}} async function run(id:string){setBusy(id);setError("");try{const run=await executeAnalysis(id);navigate(`/runs/${run.id}`)}catch(e){setError((e as Error).message);setBusy("")}} return <><header className="page-head"><div><div className="eyebrow">{PAGE_LABELS[2]}</div><h1>{ENTITY_LABELS[2]}</h1><p>选择数据资产、写下可证伪假设，再让后端执行真实算法。复核员无法触发新的运行。</p></div></header>{error&&<div className="error-box">{error}</div>}<div className="content-grid grid-main"><Panel title="新建方案"><form className="form-grid" onSubmit={create}><div className="field" style={{gridColumn:"1/-1"}}><label>方案名称</label><input value={name} onChange={e=>setName(e.target.value)}/></div><div className="field"><label>数据资产</label><select value={selected} onChange={e=>setDatasetId(e.target.value)}>{datasets.data?.items.map(item=><option value={item.id} key={item.id}>{item.name} · {item.row_count} 行</option>)}</select></div><div className="field"><label>算法口径</label><input disabled value={ALGORITHM_LABELS[0]}/></div><div className="field" style={{gridColumn:"1/-1"}}><label>可证伪假设</label><textarea value={hypothesis} onChange={e=>setHypothesis(e.target.value)}/></div><Button primary disabled={busy==="create"||!selected}>{busy==="create"?"创建中…":"创建方案"}</Button></form></Panel><Panel title="方案队列"><div className="content-grid">{analyses.data?.items.map(item=><div key={item.id}><div className="panel-head"><strong>{item.name}</strong><StatusBadge status={item.status}/></div><p className="muted">{item.hypothesis}</p><Button disabled={busy===item.id} onClick={()=>run(item.id)}>{busy===item.id?"计算中…":"运行判读"}</Button></div>)}</div></Panel></div></>; }
""",
            "src/pages/RunDetailPage.tsx": """
import { useParams } from "react-router-dom";
import { getRun } from "../api/runs";
import BarChart from "../components/common/BarChart";
import DataTable from "../components/common/DataTable";
import Panel from "../components/common/Panel";
import Stat from "../components/common/Stat";
import StatusBadge from "../components/common/StatusBadge";
import { PAGE_LABELS } from "../constants/domain";
import { useAsync } from "../hooks/useAsync";
import { checksum, dateTime } from "../utils/format";
export default function RunDetailPage(){ const {runId}=useParams(); const {data,error}=useAsync(()=>getRun(runId||""),[runId]); return <><header className="page-head"><div><div className="eyebrow">{PAGE_LABELS[3]}</div><h1>判读结果</h1></div>{data&&<StatusBadge status={data.status}/>}</header>{error&&<div className="error-box">{error}</div>}{!data?<div className="empty">正在读取结果…</div>:<div className="content-grid"><section><span className="method-tag">{data.result.method}</span><h2 className="run-headline" style={{marginTop:18}}>{data.result.headline}</h2><p className="muted" style={{maxWidth:800,lineHeight:1.8}}>{data.result.narrative}</p></section><div className="stat-row">{data.result.metrics.map(metric=><Stat key={metric.label} label={metric.label} value={metric.value} unit={metric.unit} tone={metric.tone}/>)}</div><div className="content-grid grid-main"><Panel title="效应与分组"><BarChart series={data.result.series}/></Panel><Panel title="运行证据"><div className="content-grid"><div><span className="eyebrow">checksum</span><div className="mono">{checksum(data.checksum)}</div></div><div><span className="eyebrow">created</span><p>{dateTime(data.created_at)}</p></div><div><span className="eyebrow">run id</span><div className="mono">{data.id}</div></div></div></Panel></div><Panel title="算法限制"><p className="caveat">{data.result.caveat}</p></Panel><Panel title="结果表"><DataTable rows={data.result.table}/></Panel></div>}</>; }
""",
            "src/pages/GovernancePage.tsx": """
import { listAudit } from "../api/audit";
import Panel from "../components/common/Panel";
import { PAGE_LABELS } from "../constants/domain";
import { useAsync } from "../hooks/useAsync";
import { dateTime } from "../utils/format";
export default function GovernancePage(){ const {data,error}=useAsync(listAudit); return <><header className="page-head"><div><div className="eyebrow">{PAGE_LABELS[4]}</div><h1>审计与复核</h1><p>保留资产创建、方案运行和复核动作；JWT 角色决定写入边界。</p></div><span className="method-tag">{data?.total||0} 条记录</span></header>{error&&<div className="error-box">{error}</div>}<Panel title="最近审计轨迹">{data?.items.map(item=><div className="audit-row" key={item.id}><span className="mono">{dateTime(item.created_at)}</span><strong>{item.action}</strong><span className="muted">{item.resource_type} / {item.resource_id.slice(0,12)}…</span></div>)}</Panel></>; }
""",
        }
    )
    return files


def vue_frontend(project: dict) -> dict[str, str]:
    files = frontend_common(project)
    files.update(
        {
            "package.json": """
{
  "name": "analytics-workbench-vue",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {"dev": "vite --host 0.0.0.0", "build": "vue-tsc -b && vite build", "preview": "vite preview"},
  "dependencies": {"vue": "^3.5.13", "vue-router": "^4.5.0"},
  "devDependencies": {"@vitejs/plugin-vue": "^5.2.1", "typescript": "^5.7.2", "vite": "^6.0.3", "vue-tsc": "^2.1.10"}
}
""",
            "tsconfig.json": """
{"compilerOptions":{"target":"ES2022","useDefineForClassFields":true,"module":"ESNext","moduleResolution":"Bundler","strict":true,"jsx":"preserve","resolveJsonModule":true,"isolatedModules":true,"esModuleInterop":true,"lib":["ES2022","DOM","DOM.Iterable"],"skipLibCheck":true,"noEmit":true},"include":["src/**/*.ts","src/**/*.tsx","src/**/*.vue"]}
""",
            "vite.config.ts": """
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
export default defineConfig({ plugins: [vue()], server: { port: 5173 } });
""",
            "index.html": f"""
<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>{project['name']}</title></head><body class="layout-{project['layout']}"><div id="app"></div><script type="module" src="/src/main.ts"></script></body></html>
""",
            "Dockerfile": """
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
""",
            "nginx.conf": """
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;
  location = /healthz { return 200 "ok\\n"; add_header Content-Type text/plain; }
  location /api/ { proxy_pass http://backend:8000; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; }
  location / { try_files $uri /index.html; }
}
""",
            "src/env.d.ts": """
/// <reference types="vite/client" />
""",
            "src/main.ts": """
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./styles.css";
createApp(App).use(router).mount("#app");
""",
            "src/App.vue": """
<template><RouterView /></template>
<script setup lang="ts">
import { RouterView } from "vue-router";
</script>
""",
            "src/types/index.ts": """
export type Role = "admin" | "analyst" | "reviewer";
export interface User { id:string; email:string; display_name:string; role:Role }
export interface Workspace { id:string; name:string; client_name:string; context_note:string; }
export interface Dataset { id:string; name:string; source:string; status:string; row_count:number; checksum:string; description:string; workspace_id:string; created_by:string; }
export interface Analysis { id:string; name:string; kind:string; status:string; hypothesis:string; config:Record<string,unknown>; dataset_id:string; workspace_id:string; created_by:string; }
export interface Metric { label:string; value:number|string; unit?:string; tone?:string; }
export interface Series { label:string; value:number; }
export interface RunResult { headline:string; narrative:string; metrics:Metric[]; series:Series[]; table:Record<string,unknown>[]; method:string; caveat:string; }
export interface Run { id:string; status:string; result:RunResult; metrics:Metric[]; error_message:string; checksum:string; analysis_id:string; created_at:string; }
export interface Audit { id:string; action:string; resource_type:string; resource_id:string; actor_id:string; detail:Record<string,unknown>; created_at:string; }
export interface Comment { id:string; body:string; decision:string; run_id:string; author_id:string; created_at:string; }
export interface ListResponse<T> { items:T[]; total:number; }
""",
            "src/constants/enums.ts": """
export const ROLES = { admin: "数据管理员", analyst: "分析员", reviewer: "业务复核员" } as const;
export const STATUS_LABELS: Record<string,string> = { draft:"草稿", ready:"就绪", running:"运行中", completed:"已完成", failed:"失败" };
export const NAV_ITEMS = [
  { path:"/overview", icon:"01", label:"总览" },
  { path:"/datasets", icon:"02", label:"资产" },
  { path:"/analyses", icon:"03", label:"编排" },
  { path:"/governance", icon:"04", label:"治理" },
] as const;
""",
            "src/api/client.ts": """
const TOKEN_KEY = "analytics_token";
export function getToken(){ return localStorage.getItem(TOKEN_KEY); }
export function setToken(token:string){ localStorage.setItem(TOKEN_KEY, token); }
export function clearToken(){ localStorage.removeItem(TOKEN_KEY); }
export async function api<T>(path:string, init:RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`/api${path}`, {...init, headers});
  if (!response.ok) {
    const payload = await response.json().catch(() => ({detail:"请求失败"}));
    throw new Error(payload.detail || "请求失败");
  }
  return response.json();
}
""",
            "src/api/auth.ts": """
import { api } from "./client";
import type { User } from "../types";
export async function login(email:string,password:string){ return api<{access_token:string}>("/auth/login",{method:"POST",body:JSON.stringify({email,password})}); }
export function me(){ return api<User>("/auth/me"); }
""",
            "src/api/workspace.ts": """
import { api } from "./client";
import type { Workspace } from "../types";
export const getWorkspace = () => api<Workspace>("/workspace");
""",
            "src/api/datasets.ts": """
import { api } from "./client";
import type { Dataset, ListResponse } from "../types";
export const listDatasets = () => api<ListResponse<Dataset>>("/datasets");
""",
            "src/api/analyses.ts": """
import { api } from "./client";
import type { Analysis, ListResponse, Run } from "../types";
export const listAnalyses = () => api<ListResponse<Analysis>>("/analyses");
export const createAnalysis = (payload:{name:string;dataset_id:string;kind:string;hypothesis:string;config:Record<string,unknown>}) => api<Analysis>("/analyses",{method:"POST",body:JSON.stringify(payload)});
export const executeAnalysis = (id:string) => api<Run>(`/analyses/${id}/run`,{method:"POST"});
""",
            "src/api/runs.ts": """
import { api } from "./client";
import type { Comment, ListResponse, Run } from "../types";
export const listRuns = () => api<ListResponse<Run>>("/runs");
export const getRun = (id:string) => api<Run>(`/runs/${id}`);
export const listComments = (id:string) => api<Comment[]>(`/runs/${id}/comments`);
export const addComment = (id:string,body:string,decision="pending") => api<Comment>(`/runs/${id}/comments`,{method:"POST",body:JSON.stringify({body,decision})});
""",
            "src/api/audit.ts": """
import { api } from "./client";
import type { Audit, ListResponse } from "../types";
export const listAudit = () => api<ListResponse<Audit>>("/audit");
""",
            "src/stores/auth.ts": """
import { reactive } from "vue";
import { me } from "../api/auth";
import type { User } from "../types";
export const authState = reactive<{user:User|null}>({user:null});
export async function loadUser(){ try { authState.user = await me(); } catch { authState.user = null; } }
""",
            "src/hooks/useAsync.ts": """
import { reactive } from "vue";
export function useAsync<T>(loader:()=>Promise<T>) {
  const state = reactive({
    data: null,
    error: "",
    loading: true,
    reload: async () => {
      state.loading = true;
      state.error = "";
      try {
        state.data = (await loader()) as never;
      } catch (error) {
        state.error = (error as Error).message;
      } finally {
        state.loading = false;
      }
    }
  }) as unknown as {
    data: T | null;
    error: string;
    loading: boolean;
    reload: () => Promise<void>;
  };
  state.reload();
  return state;
}
""",
            "src/hooks/useAuth.ts": """
import { onMounted } from "vue";
import { authState, loadUser } from "../stores/auth";
export function useAuth(){ onMounted(loadUser); return authState; }
""",
            "src/utils/format.ts": """
export const number = (value:number|string) => typeof value === "number" ? new Intl.NumberFormat("zh-CN",{maximumFractionDigits:3}).format(value) : value;
export const dateTime = (value:string) => value ? new Intl.DateTimeFormat("zh-CN",{dateStyle:"medium",timeStyle:"short"}).format(new Date(value)) : "—";
export const checksum = (value:string) => value ? `${value.slice(0,8)}…${value.slice(-4)}` : "—";
""",
            "src/utils/tone.ts": """
export const toneClass = (tone?:string) => tone === "positive" ? "positive" : tone === "negative" ? "negative" : "neutral";
""",
            "src/components/common/AppButton.vue": """
<template><button class="button" :class="{primary}" :disabled="disabled"><slot/></button></template>
<script setup lang="ts">
defineProps<{
  primary?: boolean;
  disabled?: boolean;
}>()
</script>
""",
            "src/components/common/AppPanel.vue": """
<template><section class="panel"><div class="panel-head"><h3>{{title}}</h3><slot name="action"/></div><slot/></section></template>
<script setup lang="ts">
defineProps<{
  title: string;
}>()
</script>
""",
            "src/components/common/StatTile.vue": """
<template><div class="stat"><div class="stat-label">{{label}}</div><div class="stat-value" :class="toneClass(tone)">{{number(value)}}<small v-if="unit" class="muted"> {{unit}}</small></div></div></template>
<script setup lang="ts">
import { number } from "../../utils/format";
import { toneClass } from "../../utils/tone";
defineProps<{
  label: string;
  value: number | string;
  unit?: string;
  tone?: string;
}>()
</script>
""",
            "src/components/common/StatusBadge.vue": """
<template><span class="status" :class="negative?'negative':positive?'positive':'neutral'">{{STATUS_LABELS[status]||status}}</span></template>
<script setup lang="ts">
import { computed } from "vue";
import { STATUS_LABELS } from "../../constants/enums";
const props = defineProps<{
  status: string;
}>();
const positive = computed(() => ["ready", "completed"].includes(props.status));
const negative = computed(() => props.status === "failed");
</script>
""",
            "src/components/common/BarChart.vue": """
<template><div v-if="series.length" class="bar-list"><div class="bar-row" v-for="item in series" :key="item.label"><span :title="item.label">{{item.label}}</span><div class="bar-track"><div class="bar-fill" :style="{width:`${Math.max(Math.abs(item.value)/max*100,3)}%`}"/></div><span class="mono">{{number(item.value)}}</span></div></div><div v-else class="empty">当前结果没有可绘制的序列。</div></template>
<script setup lang="ts">
import { computed } from "vue";
import type { Series } from "../../types";
import { number } from "../../utils/format";
const props = defineProps<{
  series: Series[];
}>();
const max = computed(() => Math.max(...props.series.map((item) => Math.abs(item.value)), 1));
</script>
""",
            "src/components/common/DataTable.vue": """
<template><div v-if="rows.length" style="overflow-x:auto"><table class="table"><thead><tr><th v-for="column in columns" :key="column">{{column}}</th></tr></thead><tbody><tr v-for="(row,index) in rows.slice(0,20)" :key="index"><td v-for="column in columns" :key="column">{{display(row[column])}}</td></tr></tbody></table></div><div v-else class="empty">暂无明细。检查数据字段后重新运行。</div></template>
<script setup lang="ts">
import { computed } from "vue";
const props = defineProps<{
  rows: Record<string, unknown>[];
}>();
const columns = computed(() => Array.from(new Set(props.rows.flatMap(Object.keys))).slice(0, 8));
const display = (value: unknown) => typeof value === "object" ? JSON.stringify(value) : String(value ?? "—");
</script>
""",
            "src/layouts/AppShell.vue": """
<template><div class="app-shell"><aside class="sidebar"><div class="brand"><div class="brand-mark">Δ</div><div><strong>{{PROJECT_NAME}}</strong><small>{{CLIENT_NAME}}</small></div></div><nav class="nav-list"><RouterLink v-for="item in NAV_ITEMS" :key="item.path" :to="item.path" class="nav-link" active-class="active"><b class="mono">{{item.icon}}</b><span>{{item.label}}</span></RouterLink></nav><div class="sidebar-foot"><div class="user-line"><span>{{auth.user?.display_name||"读取中"}}</span><span class="mono">{{auth.user?ROLES[auth.user.role]:"—"}}</span></div><AppButton @click="logout">退出登录</AppButton></div></aside><main class="main-stage"><RouterView/></main></div></template>
<script setup lang="ts">
import { RouterLink, RouterView, useRouter } from "vue-router";
import { clearToken } from "../api/client";
import { NAV_ITEMS, ROLES } from "../constants/enums";
import { CLIENT_NAME, PROJECT_NAME } from "../constants/domain";
import { useAuth } from "../hooks/useAuth";
import AppButton from "../components/common/AppButton.vue";
const auth = useAuth();
const router = useRouter();
const logout = () => {
  clearToken();
  router.push("/login");
};
</script>
""",
            "src/router/index.ts": """
import { createRouter, createWebHistory } from "vue-router";
import { getToken } from "../api/client";
import AppShell from "../layouts/AppShell.vue";
import AnalysesPage from "../pages/AnalysesPage.vue";
import DatasetsPage from "../pages/DatasetsPage.vue";
import GovernancePage from "../pages/GovernancePage.vue";
import LoginPage from "../pages/LoginPage.vue";
import OverviewPage from "../pages/OverviewPage.vue";
import RunDetailPage from "../pages/RunDetailPage.vue";
const router=createRouter({history:createWebHistory(),routes:[
 {path:"/login",component:LoginPage},
 {path:"/",component:AppShell,children:[
  {path:"overview",component:OverviewPage},{path:"datasets",component:DatasetsPage},
  {path:"analyses",component:AnalysesPage},{path:"runs/:runId",component:RunDetailPage},
  {path:"governance",component:GovernancePage}
 ]},
 {path:"/:pathMatch(.*)*",redirect:"/overview"}
]});
router.beforeEach((to)=>{if(to.path!=="/login"&&!getToken())return "/login";if(to.path==="/login"&&getToken())return "/overview";return true});
export default router;
""",
            "src/pages/LoginPage.vue": """
<template><main class="login-shell"><section class="login-thesis"><div><div class="eyebrow">Evidence-first analytics workspace</div><h1>{{PROJECT_NAME}}<br/><span class="muted">让每次判读都能回到数据。</span></h1><p class="muted" style="max-width:620px;line-height:1.8">{{CLIENT_NAME}} · {{ENTITY_LABELS[0]}} / {{ENTITY_LABELS[2]}} / {{ENTITY_LABELS[4]}}</p></div><div class="login-meta"><span>{{ALGORITHM_LABELS[0]}}</span><span>{{ALGORITHM_LABELS[1]}}</span><span>审计可追溯</span></div></section><form class="login-form" @submit.prevent="submit"><div class="eyebrow">进入工作区</div><h2>三角色演示</h2><div v-if="error" class="error-box">{{error}}</div><label>邮箱<input v-model="email" type="email" autocomplete="username"/></label><label>密码<input v-model="password" type="password" autocomplete="current-password"/></label><AppButton primary :disabled="loading">{{loading?"验证中…":"登录"}}</AppButton><p class="muted" style="font-size:11px;margin-top:20px">analyst@batchdemo.dev / reviewer@batchdemo.dev / admin@batchdemo.dev · Demo123!</p></form></main></template>
<script setup lang="ts">import { ref } from "vue"; import { useRouter } from "vue-router"; import { login } from "../api/auth"; import { setToken } from "../api/client"; import AppButton from "../components/common/AppButton.vue"; import { ALGORITHM_LABELS, CLIENT_NAME, ENTITY_LABELS, PROJECT_NAME } from "../constants/domain"; const email=ref("analyst@batchdemo.dev"); const password=ref("Demo123!"); const error=ref(""); const loading=ref(false); const router=useRouter(); async function submit(){loading.value=true;error.value="";try{const result=await login(email.value,password.value);setToken(result.access_token);router.push("/overview")}catch(e){error.value=(e as Error).message}finally{loading.value=false}}</script>
""",
            "src/pages/OverviewPage.vue": """
<template><header class="page-head"><div><div class="eyebrow">{{PAGE_LABELS[0]}}</div><h1>今天要判读什么？</h1><p>{{workspace.data?.context_note||"正在读取工作区背景…"}}</p></div><RouterLink class="button primary" to="/analyses">创建分析</RouterLink></header><div class="stat-row"><StatTile :label="ENTITY_LABELS[1]" :value="datasets.data?.total||0" unit="份"/><StatTile label="分析方案" :value="runs.data?.total||0" unit="次运行"/><StatTile label="最近状态" :value="latest?.status==='completed'?'就绪':'待运行'" :tone="latest?.status==='completed'?'positive':'neutral'"/><StatTile label="数据校验" :value="datasets.data?.items[0]?checksum(datasets.data.items[0].checksum):'—'"/></div><div class="content-grid grid-main" style="margin-top:32px"><AppPanel title="最近运行序列"><template #action><StatusBadge v-if="latest" :status="latest.status"/></template><BarChart v-if="latest?.result?.series?.length" :series="latest.result.series.slice(0,8)"/><div v-else class="empty"><div><h3>首条结果尚未生成</h3><p>从分析编排选择资产并运行。</p></div></div></AppPanel><AppPanel title="操作提示"><div class="content-grid"><div><div class="eyebrow">01 / 资产</div><p>{{datasets.data?.items[0]?.name||"等待资产加载"}}</p></div><div><div class="eyebrow">02 / 计算</div><p>所有指标由 Python 后端计算，前端只渲染返回结果。</p></div><div><div class="eyebrow">03 / 复核</div><p>最近更新时间：{{latest?dateTime(latest.created_at):"—"}}</p></div></div></AppPanel></div></template>
<script setup lang="ts">import { computed } from "vue"; import { RouterLink } from "vue-router"; import { getWorkspace } from "../api/workspace"; import { listDatasets } from "../api/datasets"; import { listRuns } from "../api/runs"; import AppPanel from "../components/common/AppPanel.vue"; import BarChart from "../components/common/BarChart.vue"; import StatTile from "../components/common/StatTile.vue"; import StatusBadge from "../components/common/StatusBadge.vue"; import { ENTITY_LABELS, PAGE_LABELS } from "../constants/domain"; import { useAsync } from "../hooks/useAsync"; import { checksum, dateTime } from "../utils/format"; const workspace=useAsync(getWorkspace); const datasets=useAsync(listDatasets); const runs=useAsync(listRuns); const latest=computed(()=>runs.data?.items[0]);</script>
""",
            "src/pages/DatasetsPage.vue": """
<template><header class="page-head"><div><div class="eyebrow">{{PAGE_LABELS[1]}}</div><h1>{{ENTITY_LABELS[1]}}</h1><p>列出可用样本、来源、行数与内容校验，确保每次运行都能定位输入版本。</p></div><span class="method-tag">{{datasets.data?.total||0}} 份资产</span></header><div v-if="datasets.error" class="error-box">{{datasets.error}}</div><div class="grid-3 content-grid"><AppPanel v-for="item in datasets.data?.items" :key="item.id" :title="item.name"><template #action><StatusBadge :status="item.status"/></template><div class="eyebrow">{{item.source}}</div><p class="muted">{{item.description}}</p><div class="stat-row stat-row-compact"><div class="stat"><div class="stat-label">样本</div><div class="stat-value">{{item.row_count.toLocaleString()}}</div></div><div class="stat"><div class="stat-label">校验</div><div class="mono" style="margin-top:12px">{{checksum(item.checksum)}}</div></div></div></AppPanel></div><div style="margin-top:34px"><AppPanel title="字段抽样"><DataTable :rows="[{name:'content_checksum',value:datasets.data?.items[0]?.checksum||'—'},{name:'role_scope',value:'admin / analyst / reviewer'},{name:'storage',value:'database JSON snapshot'}]"/></AppPanel></div></template>
<script setup lang="ts">import { listDatasets } from "../api/datasets"; import AppPanel from "../components/common/AppPanel.vue"; import DataTable from "../components/common/DataTable.vue"; import StatusBadge from "../components/common/StatusBadge.vue"; import { ENTITY_LABELS, PAGE_LABELS } from "../constants/domain"; import { useAsync } from "../hooks/useAsync"; import { checksum } from "../utils/format"; const datasets=useAsync(listDatasets);</script>
""",
            "src/pages/AnalysesPage.vue": """
<template><header class="page-head"><div><div class="eyebrow">{{PAGE_LABELS[2]}}</div><h1>{{ENTITY_LABELS[2]}}</h1><p>选择数据资产、写下可证伪假设，再让后端执行真实算法。复核员无法触发新的运行。</p></div></header><div v-if="error" class="error-box">{{error}}</div><div class="content-grid grid-main"><AppPanel title="新建方案"><form class="form-grid" @submit.prevent="create"><div class="field" style="grid-column:1/-1"><label>方案名称</label><input v-model="name"/></div><div class="field"><label>数据资产</label><select v-model="selected"><option v-for="item in datasets.data?.items" :key="item.id" :value="item.id">{{item.name}} · {{item.row_count}} 行</option></select></div><div class="field"><label>算法口径</label><input disabled :value="ALGORITHM_LABELS[0]"/></div><div class="field" style="grid-column:1/-1"><label>可证伪假设</label><textarea v-model="hypothesis"/></div><AppButton primary :disabled="busy==='create'||!selected">{{busy==="create"?"创建中…":"创建方案"}}</AppButton></form></AppPanel><AppPanel title="方案队列"><div class="content-grid"><div v-for="item in analyses.data?.items" :key="item.id"><div class="panel-head"><strong>{{item.name}}</strong><StatusBadge :status="item.status"/></div><p class="muted">{{item.hypothesis}}</p><AppButton :disabled="busy===item.id" @click="run(item.id)">{{busy===item.id?"计算中…":"运行判读"}}</AppButton></div></div></AppPanel></div></template>
<script setup lang="ts">import { ref, watch } from "vue"; import { useRouter } from "vue-router"; import { createAnalysis, executeAnalysis, listAnalyses } from "../api/analyses"; import { listDatasets } from "../api/datasets"; import AppButton from "../components/common/AppButton.vue"; import AppPanel from "../components/common/AppPanel.vue"; import StatusBadge from "../components/common/StatusBadge.vue"; import { ALGORITHM_LABELS, ENTITY_LABELS, PAGE_LABELS } from "../constants/domain"; import { useAsync } from "../hooks/useAsync"; const analyses=useAsync(listAnalyses); const datasets=useAsync(listDatasets); const name=ref(`${ALGORITHM_LABELS[0]} ${new Date().toLocaleDateString("zh-CN")}`); const selected=ref(""); const hypothesis=ref("检查主指标差异是否可以由抽样波动解释。"); const busy=ref(""); const error=ref(""); const router=useRouter(); watch(()=>datasets.data,()=>{if(!selected.value)selected.value=datasets.data?.items[0]?.id||""}); async function create(){busy.value="create";error.value="";try{await createAnalysis({name:name.value,dataset_id:selected.value,kind:"primary",hypothesis:hypothesis.value,config:{clusters:3,topics:4,min_samples:5}});await analyses.reload()}catch(e){error.value=(e as Error).message}finally{busy.value=""}} async function run(id:string){busy.value=id;error.value="";try{const run=await executeAnalysis(id);router.push(`/runs/${run.id}`)}catch(e){error.value=(e as Error).message;busy.value=""}}</script>
""",
            "src/pages/RunDetailPage.vue": """
<template><header class="page-head"><div><div class="eyebrow">{{PAGE_LABELS[3]}}</div><h1>判读结果</h1></div><StatusBadge v-if="run.data" :status="run.data.status"/></header><div v-if="run.error" class="error-box">{{run.error}}</div><div v-if="!run.data" class="empty">正在读取结果…</div><div v-else class="content-grid"><section><span class="method-tag">{{run.data.result.method}}</span><h2 class="run-headline" style="margin-top:18px">{{run.data.result.headline}}</h2><p class="muted" style="max-width:800px;line-height:1.8">{{run.data.result.narrative}}</p></section><div class="stat-row"><StatTile v-for="metric in run.data.result.metrics" :key="metric.label" :label="metric.label" :value="metric.value" :unit="metric.unit" :tone="metric.tone"/></div><div class="content-grid grid-main"><AppPanel title="效应与分组"><BarChart :series="run.data.result.series"/></AppPanel><AppPanel title="运行证据"><div class="content-grid"><div><span class="eyebrow">checksum</span><div class="mono">{{checksum(run.data.checksum)}}</div></div><div><span class="eyebrow">created</span><p>{{dateTime(run.data.created_at)}}</p></div><div><span class="eyebrow">run id</span><div class="mono">{{run.data.id}}</div></div></div></AppPanel></div><AppPanel title="算法限制"><p class="caveat">{{run.data.result.caveat}}</p></AppPanel><AppPanel title="结果表"><DataTable :rows="run.data.result.table"/></AppPanel></div></template>
<script setup lang="ts">import { useRoute } from "vue-router"; import { getRun } from "../api/runs"; import AppPanel from "../components/common/AppPanel.vue"; import BarChart from "../components/common/BarChart.vue"; import DataTable from "../components/common/DataTable.vue"; import StatTile from "../components/common/StatTile.vue"; import StatusBadge from "../components/common/StatusBadge.vue"; import { PAGE_LABELS } from "../constants/domain"; import { useAsync } from "../hooks/useAsync"; import { checksum, dateTime } from "../utils/format"; const route=useRoute(); const run=useAsync(()=>getRun(String(route.params.runId)));</script>
""",
            "src/pages/GovernancePage.vue": """
<template><header class="page-head"><div><div class="eyebrow">{{PAGE_LABELS[4]}}</div><h1>审计与复核</h1><p>保留资产创建、方案运行和复核动作；JWT 角色决定写入边界。</p></div><span class="method-tag">{{governance.data?.total||0}} 条记录</span></header><div v-if="governance.error" class="error-box">{{governance.error}}</div><AppPanel title="最近审计轨迹"><div v-for="item in governance.data?.items" :key="item.id" class="audit-row"><span class="mono">{{dateTime(item.created_at)}}</span><strong>{{item.action}}</strong><span class="muted">{{item.resource_type}} / {{item.resource_id.slice(0,12)}}…</span></div></AppPanel></template>
<script setup lang="ts">import { listAudit } from "../api/audit"; import AppPanel from "../components/common/AppPanel.vue"; import { PAGE_LABELS } from "../constants/domain"; import { useAsync } from "../hooks/useAsync"; import { dateTime } from "../utils/format"; const governance=useAsync(listAudit);</script>
""",
        }
    )
    return files


def screenshot_script(project: dict) -> str:
    return f'''
const {{ chromium }} = require("../../node_modules/playwright");
const fs = require("fs");
const path = require("path");

const base = process.env.BASE_URL || "http://localhost:{ports(project)[0]}";
const out = process.env.SCREENSHOT_DIR || path.join(__dirname, "..", "screenshots");
fs.mkdirSync(out, {{ recursive: true }});

(async () => {{
  const browser = await chromium.launch({{ headless: true }});
  const page = await browser.newPage({{ viewport: {{ width: 1440, height: 900 }}, deviceScaleFactor: 1 }});
  const consoleErrors = [];
  page.on("console", (msg) => {{ if (msg.type() === "error") consoleErrors.push(msg.text()); }});
  await page.goto(`${{base}}/login`, {{ waitUntil: "networkidle" }});
  await page.screenshot({{ path: path.join(out, "01-login.png"), fullPage: false }});
  await page.getByRole("button", {{ name: "登录" }}).click();
  await page.waitForURL("**/overview", {{ timeout: 30000 }});
  await page.waitForSelector(".stat-row", {{ timeout: 30000 }});
  await page.waitForLoadState("networkidle");
  await page.screenshot({{ path: path.join(out, "02-overview.png"), fullPage: false }});
  await page.getByRole("link", {{ name: /资产/ }}).click();
  await page.waitForURL("**/datasets");
  await page.waitForLoadState("networkidle");
  await page.screenshot({{ path: path.join(out, "03-datasets.png"), fullPage: false }});
  await page.getByRole("link", {{ name: /编排/ }}).click();
  await page.waitForURL("**/analyses");
  await page.waitForSelector(".grid-main", {{ timeout: 30000 }});
  await page.waitForLoadState("networkidle");
  await page.screenshot({{ path: path.join(out, "04-analyses.png"), fullPage: false }});

  const token = await page.evaluate(() => localStorage.getItem("analytics_token"));
  const headers = {{ "Content-Type": "application/json", Authorization: `Bearer ${{token}}` }};
  const analyses = await page.evaluate(async (headers) => {{
    const response = await fetch("/api/analyses", {{ headers }});
    if (!response.ok) throw new Error(`analysis list failed: ${{response.status}}`);
    return response.json();
  }}, headers);
  if (!analyses.items?.length) throw new Error("seed analysis missing");
  const run = await page.evaluate(async ({{ id, headers }}) => {{
    const response = await fetch(`/api/analyses/${{id}}/run`, {{ method: "POST", headers }});
    if (!response.ok) throw new Error(`run failed: ${{response.status}} ${{await response.text()}}`);
    return response.json();
  }}, {{ id: analyses.items[0].id, headers }});
  await page.goto(`${{base}}/runs/${{run.id}}`, {{ waitUntil: "networkidle" }});
  await page.waitForSelector(".run-headline", {{ timeout: 30000 }});
  await page.screenshot({{ path: path.join(out, "05-result.png"), fullPage: true }});
  await page.screenshot({{ path: path.join(out, "06-result-viewport.png"), fullPage: false }});
  fs.writeFileSync(path.join(out, "console-errors.json"), JSON.stringify(consoleErrors, null, 2));
  console.log(JSON.stringify({{ screenshots: 6, runId: run.id, consoleErrors: consoleErrors.length }}, null, 2));
  await browser.close();
}})().catch((error) => {{ console.error(error); process.exit(1); }});
'''


def smoke_script(project: dict) -> str:
    be = ports(project)[1]
    return f'''#!/usr/bin/env bash
set -euo pipefail
BASE="${{BACKEND_URL:-http://localhost:{be}}}"
LOG_DIR="${{LOG_DIR:-$(pwd)}}"
mkdir -p "$LOG_DIR"

login() {{
  local email="$1"
  curl -fsS -X POST "$BASE/api/auth/login" -H 'Content-Type: application/json' \\
    -d "{{\\"email\\":\\"$email\\",\\"password\\":\\"Demo123!\\"}}"
}}

ADMIN="$(login admin@batchdemo.dev)"
ANALYST="$(login analyst@batchdemo.dev)"
REVIEWER="$(login reviewer@batchdemo.dev)"
printf '%s\\n' "$ADMIN" "$ANALYST" "$REVIEWER" > "$LOG_DIR/logins.jsonl"
ANALYST_TOKEN="$(printf '%s' "$ANALYST" | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')"
REVIEWER_TOKEN="$(printf '%s' "$REVIEWER" | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')"

DATASETS="$(curl -fsS "$BASE/api/datasets" -H "Authorization: Bearer $ANALYST_TOKEN")"
printf '%s' "$DATASETS" > "$LOG_DIR/datasets.json"
ANALYSES="$(curl -fsS "$BASE/api/analyses" -H "Authorization: Bearer $ANALYST_TOKEN")"
printf '%s' "$ANALYSES" > "$LOG_DIR/analyses-before.json"
ANALYSIS_ID="$(printf '%s' "$ANALYSES" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["items"][0]["id"])')"

curl -fsS -X POST "$BASE/api/analyses/$ANALYSIS_ID/run" \\
  -H "Authorization: Bearer $ANALYST_TOKEN" \\
  -H 'Content-Type: application/json' > "$LOG_DIR/run-main.json"

DATASET_ID="$(printf '%s' "$DATASETS" | python3 -c 'import json,sys;print(json.load(sys.stdin)["items"][0]["id"])')"
REVIEWER_STATUS="$(curl -sS -o "$LOG_DIR/reviewer-forbidden.json" -w '%{{http_code}}' \\
  -X POST "$BASE/api/analyses" -H "Authorization: Bearer $REVIEWER_TOKEN" \\
  -H 'Content-Type: application/json' \\
  -d "{{\\"name\\":\\"复核员不应创建\\",\\"dataset_id\\":\\"$DATASET_ID\\"}}")"
if [ "$REVIEWER_STATUS" != "403" ]; then
  echo "reviewer permission expected 403, got $REVIEWER_STATUS" >&2
  exit 1
fi

curl -fsS "$BASE/api/audit" -H "Authorization: Bearer $ANALYST_TOKEN" > "$LOG_DIR/audit.json"
echo "smoke passed: three logins, analyst run, reviewer 403, audit readable"
'''


def testing_template(project: dict) -> str:
    return f"""
# {project['name']} 测试记录

> 本文件由批次 QA 在真实容器运行后补充。未执行的项目不得写成“全部通过”。

## 环境

- 日期：待执行
- 前端 / 后端 / 数据库端口：{ports(project)[0]}/{ports(project)[1]}/{ports(project)[2]}
- Docker：待执行
- 浏览器：Playwright Chromium，1440×900

## 结果

| 检查 | 结果 | 证据 |
|---|---|---|
| `docker compose config --quiet` | 待执行 | — |
| 5 服务健康 | 待执行 | — |
| seed 连续两次幂等 | 待执行 | — |
| 三账号登录与权限差异 | 待执行 | — |
| 主流程创建 → 执行 → 结果 | 待执行 | — |
| 5 张真实截图 | 待执行 | — |

## 已有基线

- 代码路径已生成，真实结果由自动 QA 覆盖。
- 数据规模与算法 seed 固定，重复运行使用自然键避免新增。

## 已知差异

- 待真实执行后填写。
"""


def generate_project(project: dict) -> None:
    pid = project_id(project)
    root = ROOT / "projects" / pid
    artifacts = ROOT / "test-artifacts" / pid
    fe, be, db = ports(project)
    write(root / "docker-compose.yml", compose_file(project))
    env, env_example = env_files(project)
    write(root / ".env", env)
    write(root / ".env.example", env_example)
    write(root / ".gitignore", """
.env
node_modules/
dist/
__pycache__/
*.pyc
.venv/
artifacts/
uploads/
logs/
*.log
.DS_Store
""")
    write(root / "README.md", readme_source(project))

    combined_backend = backend_files(project)
    combined_backend.update(backend_runtime_files(project))
    combined_backend["src/services/analysis_engine.py"] = analysis_engine_source(project)
    combined_backend["scripts/demo_data.py"] = demo_data_source(project)
    combined_backend["scripts/seed_demo.py"] = seed_source(project)
    for path, content in combined_backend.items():
        write(root / "backend" / path, content)
    write(root / "backend/.dockerignore", """
.env
__pycache__/
*.pyc
.venv/
artifacts/
""")

    frontend = react_frontend(project) if project["frontend"] == "react" else vue_frontend(project)
    for path, content in frontend.items():
        write(root / "frontend" / path, content)
    write(root / "frontend/.dockerignore", """
node_modules/
dist/
.env
*.log
""")

    write(artifacts / "tests/screenshots.cjs", screenshot_script(project))
    write(artifacts / "tests/smoke.sh", smoke_script(project))
    write(artifacts / "TESTING.md", testing_template(project))


def generate_qa_assets() -> None:
    write(ROOT / "test-artifacts/package.json", """
{
  "name": "batch-screenshot-runner",
  "private": true,
  "dependencies": {"playwright": "1.49.1"}
}
""")
    write(ROOT / "scripts/qa_project.sh", r'''
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
''')

    write(ROOT / "README-batch.md", """
# 25 项数据分析批次

本工作区包含 25 个中型全栈数据分析项目。由于技能单批上限为 10，输入拆成：

- `batch-prompts-01.txt`：1-10
- `batch-prompts-02.txt`：11-20
- `batch-prompts-03.txt`：21-25

统一端口全局连续分配；`scripts/qa_project.sh` 使用共享槽位，最多运行 3 个 Docker 栈。

```bash
python3 scripts/generate_batch.py
python3 /Users/ali/.codex/skills/pr-batch-project/scripts/validate_batch.py batch-prompts-01.txt
python3 /Users/ali/.codex/skills/pr-batch-project/scripts/validate_batch.py batch-prompts-02.txt
python3 /Users/ali/.codex/skills/pr-batch-project/scripts/validate_batch.py batch-prompts-03.txt
bash scripts/qa_project.sh gb-7001
```
""")
    write(ROOT / "BATCH-REPORT.md", """
# 批次报告 batch-20261113-data-analytics-25

- 输入：25 条中型数据分析短提示词，拆成 10 / 10 / 5。
- 日期：2026-11-13
- 并发：最多 3 个 Docker 栈。
- 状态：生成中，待逐项真实 QA 后更新。

| 编号 | 选题 | 状态 | 截图 | 主流程 | 已知差异 |
|---|---|---|---|---|---|
""")


def main() -> None:
    validate_config()
    generate_prompt_files()
    generate_plan()
    generate_qa_assets()
    for project in PROJECTS:
        generate_project(project)
    print(f"generated {len(PROJECTS)} projects")


if __name__ == "__main__":
    main()



