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



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
