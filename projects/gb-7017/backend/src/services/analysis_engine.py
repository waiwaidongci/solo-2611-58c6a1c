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



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
