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
    grouped: dict[str, dict[str, float]] = {}
    for row in rows:
        group = str(row.get("group", "B"))
        bucket = grouped.setdefault(group, {"exposure": 0.0, "conversion": 0.0})
        bucket["exposure"] += float(row.get("exposure", row.get("users", 0)))
        bucket["conversion"] += float(row.get("conversion", row.get("converted", 0)))
    if len(grouped) < 2:
        raise ValueError("至少需要两个实验组")
    ordered = sorted(grouped.items(), key=lambda item: item[0])
    (control_name, control), (variant_name, variant) = ordered[:2]
    p1 = control["conversion"] / max(control["exposure"], 1)
    p2 = variant["conversion"] / max(variant["exposure"], 1)
    pooled = (control["conversion"] + variant["conversion"]) / max(
        control["exposure"] + variant["exposure"], 1
    )
    se = math.sqrt(max(pooled * (1 - pooled) * (1 / control["exposure"] + 1 / variant["exposure"]), 1e-12))
    z_value = (p2 - p1) / se
    p_value = math.erfc(abs(z_value) / math.sqrt(2))
    rng = np.random.default_rng(42)
    posterior = rng.beta(variant["conversion"] + 1, variant["exposure"] - variant["conversion"] + 1, 20000)
    prior = rng.beta(control["conversion"] + 1, control["exposure"] - control["conversion"] + 1, 20000)
    prob_better = float((posterior > prior).mean())
    lift = (p2 - p1) / max(p1, 1e-9)
    return _envelope(
        f"{variant_name} 比 {control_name} 的相对提升为 {lift:.1%}",
        f"两比例 z 检验 p={p_value:.4f}，后验胜率 {prob_better:.1%}。结论需结合实验预注册停止规则。",
        [
            _metric("相对提升", lift * 100, "%", "positive" if lift > 0 else "negative"),
            _metric("双侧 p 值", p_value, "", "positive" if p_value < 0.05 else "neutral"),
            _metric("后验胜率", prob_better * 100, "%", "positive" if prob_better > 0.9 else "neutral"),
            _metric("样本量", control["exposure"] + variant["exposure"], "人", "neutral"),
        ],
        [_series(control_name, p1 * 100), _series(variant_name, p2 * 100)],
        [
            {"label": name, "rate": round(value["conversion"] / max(value["exposure"], 1) * 100, 3),
             "exposure": int(value["exposure"]), "conversion": int(value["conversion"])}
            for name, value in ordered
        ],
        "two_proportion_z + beta_binomial",
        "观察性运行不能替代随机分流检查；连续偷看结果会抬高假阳性。",
    )



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
