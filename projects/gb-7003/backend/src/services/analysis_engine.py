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
    groups: dict[str, list[float]] = {}
    for row in rows:
        try:
            groups.setdefault(str(row.get("batch", "A")), []).append(float(row["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    names = sorted(groups)
    if len(names) < 2:
        raise ValueError("至少需要两个比较批次")
    control = groups[names[0]]
    records = []
    for name in names[1:]:
        test = stats.ttest_ind(groups[name], control, equal_var=False, nan_policy="omit")
        mean_diff = float(np.mean(groups[name]) - np.mean(control))
        records.append({"label": name, "diff": mean_diff, "p_value": float(test.pvalue)})
    p_values = np.asarray([item["p_value"] for item in records])
    order = np.argsort(p_values)
    running = 1.0
    q_values = np.empty_like(p_values)
    for rank in range(len(order) - 1, -1, -1):
        idx = order[rank]
        running = min(running, p_values[idx] * len(p_values) / (rank + 1))
        q_values[idx] = running
    for record, q_value in zip(records, q_values):
        record["q_value"] = float(q_value)
    records.sort(key=lambda item: abs(item["diff"]), reverse=True)
    top = records[0]
    return _envelope(
        f"{top['label']} 与 {names[0]} 的均值差最大：{top['diff']:+.3f}",
        f"Welch t 检验后使用 BH 控制批量假发现，最小 q={min(q_values):.4f}。",
        [
            _metric("最大均值差", top["diff"], "", "positive" if abs(top["diff"]) > 0 else "neutral"),
            _metric("最小 q 值", min(q_values), "", "positive" if min(q_values) < .05 else "neutral"),
            _metric("比较组数", len(records), "组", "neutral"),
            _metric("总样本", sum(len(values) for values in groups.values()), "份", "neutral"),
        ],
        [_series(item["label"], round(item["diff"], 4)) for item in records],
        [{"label": item["label"], "mean_diff": round(item["diff"], 4),
          "p_value": round(item["p_value"], 5), "q_value": round(item["q_value"], 5)} for item in records],
        "welch_t + bh_fdr",
        "小样本试验仍需检查异常值和田间空间效应；q 值不是效应大小。",
    )



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
