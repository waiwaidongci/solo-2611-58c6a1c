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



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
