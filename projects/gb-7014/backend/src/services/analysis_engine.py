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



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
