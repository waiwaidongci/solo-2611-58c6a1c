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



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
