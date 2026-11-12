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
    paths = []
    for row in rows:
        path = row.get("path", [])
        if isinstance(path, list) and path:
            outcome = "Conversion" if int(row.get("converted", 1)) else "Null"
            paths.append(["Start"] + [str(item) for item in path] + [outcome])
    if len(paths) < 10:
        raise ValueError("转化路径不足")

    def transition_probability(remove_channel: str | None = None) -> float:
        counts: dict[str, dict[str, int]] = {}
        for path in paths:
            filtered = [state for state in path if state != remove_channel]
            for left, right in zip(filtered, filtered[1:]):
                counts.setdefault(left, {}).setdefault(right, 0)
                counts[left][right] += 1
        states = sorted(set(counts) | {target for edges in counts.values() for target in edges})
        transient = [state for state in states if state not in ("Conversion", "Null")]
        if "Start" not in transient:
            return 0.0
        index = {state: position for position, state in enumerate(transient)}
        q_matrix = np.zeros((len(transient), len(transient)), dtype=float)
        r_conversion = np.zeros(len(transient), dtype=float)
        for source, edges in counts.items():
            if source not in index:
                continue
            total = max(sum(edges.values()), 1)
            row = index[source]
            for target, count in edges.items():
                probability = count / total
                if target == "Conversion":
                    r_conversion[row] += probability
                elif target in index:
                    q_matrix[row, index[target]] += probability
        try:
            fundamental = np.linalg.inv(np.eye(len(transient)) - q_matrix)
        except np.linalg.LinAlgError:
            return 0.0
        return float(fundamental[index["Start"]] @ r_conversion)

    baseline = transition_probability(None)
    channels = sorted({channel for path in paths for channel in path[1:-1]})
    records = []
    for channel in channels:
        without = transition_probability(channel)
        records.append({"label": channel, "removal": abs(baseline - without) / max(baseline, 1e-9)})
    total = sum(item["removal"] for item in records) or 1
    for item in records:
        item["share"] = item["removal"] / total
    records.sort(key=lambda item: item["share"], reverse=True)
    top = records[0]
    return _envelope(
        f"{top['label']} 的移除效应最高，贡献 {top['share']:.1%}",
        f"基线 Markov 转化概率 {baseline:.1%}，按移除后的转化概率变化幅度归一化。",
        [
            _metric("基线转化", baseline * 100, "%", "neutral"),
            _metric("首要渠道", top["share"] * 100, "%", "positive"),
            _metric("渠道数", len(records), "个", "neutral"),
            _metric("路径数", len(paths), "条", "neutral"),
        ],
        [_series(item["label"], round(item["share"] * 100, 3)) for item in records],
        [{"label": item["label"], "removal_effect": round(item["removal"], 5),
          "share": round(item["share"], 5)} for item in records],
        "markov_transition + removal_effect",
        "归因依赖路径完整采集；离线曝光与跨设备身份合并偏差会改变结果。",
    )



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
