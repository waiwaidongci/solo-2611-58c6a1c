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



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
