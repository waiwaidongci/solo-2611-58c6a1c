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
    return {"label": label, "value": value, "unit": unit, "tone": tone}


def _series(label, value):
    return {"label": str(label), "value": float(value)}


def _envelope(headline, narrative, metrics, series, table, method, caveat):
    return {
        "headline": headline,
        "narrative": narrative,
        "metrics": metrics,
        "series": series,
        "table": table,
        "method": method,
        "caveat": caveat,
    }


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



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
