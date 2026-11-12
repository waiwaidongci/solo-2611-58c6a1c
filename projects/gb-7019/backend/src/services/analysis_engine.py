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



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
