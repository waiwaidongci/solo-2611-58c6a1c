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
    score = np.asarray([float(row.get("score", 0)) for row in rows])
    if len(set(target.tolist())) < 2:
        raise ValueError("需要正负样本")
    fpr, tpr, thresholds = roc_curve(target, score)
    j_scores = tpr - fpr
    index = int(np.argmax(j_scores))
    threshold = float(thresholds[index])
    predicted = (score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(target, predicted).ravel()
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    pass_rate = float((score >= threshold).mean())
    return _envelope(
        f"Youden J 最优阈值 {threshold:.3f}，通过率 {pass_rate:.1%}",
        f"命中 Recall {recall:.1%}，精确率 {precision:.1%}；业务还需设定可接受坏账成本。",
        [
            _metric("最优阈值", threshold, "", "positive"),
            _metric("Recall", recall * 100, "%", "positive"),
            _metric("Precision", precision * 100, "%", "neutral"),
            _metric("通过率", pass_rate * 100, "%", "neutral"),
        ],
        [{"label": f"TPR {tpr[i]:.2f}", "value": float(tpr[i])} for i in np.linspace(0, len(tpr) - 1, 10, dtype=int)],
        [{"label": "混淆矩阵", "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
          "threshold": round(threshold, 5)}],
        "roc_curve + youden_j + confusion_matrix",
        "历史标签存在表现期偏差；上线阈值要按近期样本和业务成本重新评审。",
    )



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
