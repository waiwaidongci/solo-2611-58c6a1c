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



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
