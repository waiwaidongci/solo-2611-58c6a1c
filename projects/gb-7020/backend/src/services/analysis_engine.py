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
            groups.setdefault(str(row.get("line", "A线")), []).append(float(row["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    if len(groups) < 2:
        raise ValueError("至少需要两个产线组")
    values = list(groups.values())
    test = stats.f_oneway(*values)
    total_n = sum(len(item) for item in values)
    df_within = total_n - len(values)
    mse = sum(np.var(item, ddof=1) * (len(item) - 1) for item in values) / max(df_within, 1)
    names = sorted(groups)
    pairs = []
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            diff = float(np.mean(groups[left]) - np.mean(groups[right]))
            se = math.sqrt(mse * (1 / len(groups[left]) + 1 / len(groups[right])))
            q_value = abs(diff) / max(se, 1e-9) * math.sqrt(2)
            p_value = float(stats.studentized_range.sf(q_value, len(values), max(df_within, 1)))
            pairs.append({"left": left, "right": right, "diff": diff, "p_value": p_value})
    pairs.sort(key=lambda item: abs(item["diff"]), reverse=True)
    top = pairs[0]
    return _envelope(
        f"ANOVA p={test.pvalue:.4f}，最大差异 {top['left']} vs {top['right']}",
        f"Tukey 成对比较中最小 p={min(item['p_value'] for item in pairs):.4f}。",
        [
            _metric("ANOVA p 值", test.pvalue, "", "positive" if test.pvalue < .05 else "neutral"),
            _metric("最大均值差", top["diff"], "", "negative" if abs(top["diff"]) > 0 else "neutral"),
            _metric("Tukey 最小 p", min(item["p_value"] for item in pairs), "", "neutral"),
            _metric("总样本", total_n, "份", "neutral"),
        ],
        [_series(name, round(float(np.mean(groups[name])), 4)) for name in names],
        [{"label": f"{item['left']} vs {item['right']}", "mean_diff": round(item["diff"], 4),
          "p_value": round(item["p_value"], 5)} for item in pairs],
        "one_way_anova + tukey_hsd",
        "检测样本应满足独立抽样假设；同一批次重复测量需要改用混合模型。",
    )



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
