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
    definitions: dict[str, list[dict]] = {}
    for row in rows:
        name = str(row.get("name", "")).strip()
        if name:
            definitions.setdefault(name, []).append(row)
    conflicts = []
    for name, items in definitions.items():
        hashes = {str(item.get("definition_hash", item.get("definition", ""))) for item in items}
        if len(hashes) > 1:
            conflicts.append({"label": name, "versions": len(hashes)})
    graph = {name: [str(dep) for dep in items[0].get("deps", [])] for name, items in definitions.items()}
    indegree = {name: 0 for name in graph}
    for name, deps in graph.items():
        for dep in deps:
            if dep in indegree:
                indegree[name] += 1
    queue = sorted([name for name, degree in indegree.items() if degree == 0])
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for other, deps in graph.items():
            if node in deps:
                indegree[other] -= 1
                if indegree[other] == 0:
                    queue.append(other)
    cyclic = len(order) != len(graph)
    return _envelope(
        f"登记 {len(graph)} 个指标，发现 {len(conflicts)} 个同名冲突",
        "依赖关系必须可拓扑排序；存在环时下游报表不得自动发布。",
        [
            _metric("指标数", len(graph), "个", "neutral"),
            _metric("同名冲突", len(conflicts), "个", "negative" if conflicts else "positive"),
            _metric("依赖环", 1 if cyclic else 0, "个", "negative" if cyclic else "positive"),
            _metric("可执行顺序", len(order), "个", "positive"),
        ],
        [_series(name, len(graph[name])) for name in order[:10]],
        [{"label": name, "deps": graph[name], "position": order.index(name) if name in order else -1}
         for name in sorted(graph)],
        "metric_dag + definition_hash_conflict",
        "定义哈希只能发现文本差异，口径等价性仍需数据域负责人复核。",
    )



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
