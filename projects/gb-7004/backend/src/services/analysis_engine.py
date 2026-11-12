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
    periods: dict[str, list[float]] = {}
    for row in rows:
        try:
            periods.setdefault(str(row.get("period", "reference")), []).append(float(row["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    if "reference" not in periods or "current" not in periods:
        raise ValueError("需要 reference 与 current 两个分布")
    ref = np.asarray(periods["reference"])
    cur = np.asarray(periods["current"])
    ks = stats.ks_2samp(ref, cur)
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, 11)))
    ref_counts, _ = np.histogram(ref, bins=edges)
    cur_counts, _ = np.histogram(cur, bins=edges)
    ref_share = np.maximum(ref_counts / max(ref_counts.sum(), 1), 1e-6)
    cur_share = np.maximum(cur_counts / max(cur_counts.sum(), 1), 1e-6)
    psi = float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))
    return _envelope(
        f"KS 距离 {ks.statistic:.3f}，PSI {psi:.3f}",
        "PSI < 0.1 视为稳定，0.1-0.25 需复核，超过 0.25 需要处置。",
        [
            _metric("KS 距离", ks.statistic, "", "negative" if ks.statistic > .15 else "neutral"),
            _metric("KS p 值", ks.pvalue, "", "neutral"),
            _metric("PSI", psi, "", "negative" if psi > .25 else "positive" if psi < .1 else "neutral"),
            _metric("当前样本", len(cur), "份", "neutral"),
        ],
        [_series(f"分箱 {index + 1}", round((cur_share[index] - ref_share[index]) * 100, 3))
         for index in range(len(ref_share))],
        [{"label": f"分箱 {index + 1}", "reference": round(ref_share[index], 5),
          "current": round(cur_share[index], 5)} for index in range(len(ref_share))],
        "ks_2samp + population_stability_index",
        "漂移不等同于质量失控；试剂批号变更应先与质控规则联动解释。",
    )



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
