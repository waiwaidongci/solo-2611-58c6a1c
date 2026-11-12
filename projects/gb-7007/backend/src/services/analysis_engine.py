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
    matrix = np.asarray([[float(row.get(key, 0)) for key in ("tenure", "usage", "tickets", "login_gap")]
                         for row in rows], dtype=float)
    target = np.asarray([int(row.get("churned", 0)) for row in rows], dtype=int)
    if len(set(target.tolist())) < 2:
        raise ValueError("流失标签只有一个类别")
    model = LogisticRegression(max_iter=800, class_weight="balanced", random_state=42)
    model.fit(StandardScaler().fit_transform(matrix), target)
    probability = model.predict_proba(StandardScaler().fit(matrix).transform(matrix))[:, 1]
    auc_value = roc_auc_score(target, probability)
    rng = np.random.default_rng(42)
    boot = []
    for _ in range(120):
        idx = rng.integers(0, len(target), len(target))
        if len(set(target[idx].tolist())) < 2:
            continue
        boot.append(roc_auc_score(target[idx], probability[idx]))
    low, high = np.quantile(boot, [0.025, 0.975])
    feature_effect = sorted(
        [{"label": name, "value": float(coef)} for name, coef in
         zip(("在网月数", "周使用时长", "近90天工单", "登录间隔"), model.coef_[0])],
        key=lambda item: abs(item["value"]), reverse=True
    )
    risk_count = int((probability >= .6).sum())
    return _envelope(
        f"识别 {risk_count} 个高流失风险账户，AUC {auc_value:.3f}",
        f"Bootstrap 95% 区间 {low:.3f}-{high:.3f}；分数用于排序触达名单。",
        [
            _metric("ROC AUC", auc_value, "", "positive" if auc_value > .75 else "neutral"),
            _metric("95% 下限", low, "", "neutral"),
            _metric("高风险账户", risk_count, "户", "negative"),
            _metric("样本量", len(rows), "户", "neutral"),
        ],
        [_series(item["label"], round(item["value"], 3)) for item in feature_effect],
        [{"label": item["label"], "coefficient": round(item["value"], 4)} for item in feature_effect],
        "weighted_logistic + bootstrap_auc",
        "同一客户不得跨训练集和验证集；当前结果为演示集内评估。",
    )



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
