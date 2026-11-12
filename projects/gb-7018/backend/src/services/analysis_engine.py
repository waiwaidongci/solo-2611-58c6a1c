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



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
