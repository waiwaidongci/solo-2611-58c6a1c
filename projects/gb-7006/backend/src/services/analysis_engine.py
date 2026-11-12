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
    baskets = []
    for row in rows:
        items = row.get("items", [])
        if isinstance(items, list):
            baskets.append({str(item) for item in items if str(item).strip()})
    if len(baskets) < 20:
        raise ValueError("购物篮样本不足")
    min_support = float(config.get("min_support", 0.02))
    pair_counts: dict[tuple[str, str], int] = {}
    item_counts: dict[str, int] = {}
    for basket in baskets:
        for item in basket:
            item_counts[item] = item_counts.get(item, 0) + 1
        for left, right in itertools.combinations(sorted(basket), 2):
            pair_counts[(left, right)] = pair_counts.get((left, right), 0) + 1
    records = []
    for (left, right), count in pair_counts.items():
        support = count / len(baskets)
        if support < min_support:
            continue
        confidence = count / max(item_counts[left], 1)
        reverse_conf = count / max(item_counts[right], 1)
        lift = confidence / max(item_counts[right] / len(baskets), 1e-9)
        records.append({"left": left, "right": right, "support": support,
                        "confidence": confidence, "reverse_confidence": reverse_conf, "lift": lift})
    if not records:
        raise ValueError("当前支持度阈值下没有规则")
    records.sort(key=lambda item: item["lift"], reverse=True)
    top = records[0]
    return _envelope(
        f"{top['left']} → {top['right']} 的提升度最高：{top['lift']:.2f}",
        f"从 {len(baskets)} 个购物篮中保留 {len(records)} 条达到最小支持度的关联规则。",
        [
            _metric("最高 Lift", top["lift"], "", "positive"),
            _metric("支持度", top["support"] * 100, "%", "neutral"),
            _metric("置信度", top["confidence"] * 100, "%", "positive"),
            _metric("有效规则", len(records), "条", "neutral"),
        ],
        [_series(f"{item['left']}→{item['right']}", round(item["lift"], 3)) for item in records[:10]],
        [{"label": f"{item['left']} → {item['right']}", "support": round(item["support"], 4),
          "confidence": round(item["confidence"], 4), "lift": round(item["lift"], 4)}
         for item in records[:20]],
        "apriori_pairs + lift",
        "提升度只描述同篮共现，陈列动作仍要通过门店级对照实验验证。",
    )



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
