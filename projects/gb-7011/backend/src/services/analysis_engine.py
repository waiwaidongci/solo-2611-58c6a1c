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
    summary: dict[str, dict[str, float]] = {}
    for row in rows:
        region = str(row.get("region", "未分组"))
        period = str(row.get("period", "current"))
        bucket = summary.setdefault(region, {"base_orders": 0, "base_revenue": 0, "base_cost": 0,
                                              "cur_orders": 0, "cur_revenue": 0, "cur_cost": 0})
        prefix = "base" if period == "base" else "cur"
        bucket[f"{prefix}_orders"] += float(row.get("orders", 0))
        bucket[f"{prefix}_revenue"] += float(row.get("revenue", 0))
        bucket[f"{prefix}_cost"] += float(row.get("cost", 0))
    records = []
    for region, item in summary.items():
        base_price = item["base_revenue"] / max(item["base_orders"], 1)
        cur_price = item["cur_revenue"] / max(item["cur_orders"], 1)
        price_effect = (cur_price - base_price) * item["cur_orders"]
        volume_effect = (item["cur_orders"] - item["base_orders"]) * base_price
        base_profit = item["base_revenue"] - item["base_cost"]
        cur_profit = item["cur_revenue"] - item["cur_cost"]
        records.append({"label": region, "profit": cur_profit,
                        "margin": cur_profit / max(item["cur_revenue"], 1),
                        "price_effect": price_effect, "volume_effect": volume_effect,
                        "delta": cur_profit - base_profit})
    records.sort(key=lambda item: item["profit"], reverse=True)
    total_delta = sum(item["delta"] for item in records)
    price_total = sum(item["price_effect"] for item in records)
    volume_total = sum(item["volume_effect"] for item in records)
    return _envelope(
        f"利润变化 {total_delta:+,.0f} 元，价格贡献 {price_total:+,.0f}",
        "按线路区域汇总运单，并把利润变化拆为价格与业务量两因素。",
        [
            _metric("利润变化", total_delta, "元", "positive" if total_delta >= 0 else "negative"),
            _metric("价格贡献", price_total, "元", "neutral"),
            _metric("业务量贡献", volume_total, "元", "neutral"),
            _metric("区域数", len(records), "个", "neutral"),
        ],
        [_series(item["label"], round(item["delta"], 2)) for item in records],
        [{"label": item["label"], "profit": round(item["profit"], 2),
          "margin": round(item["margin"], 4), "price_effect": round(item["price_effect"], 2),
          "volume_effect": round(item["volume_effect"], 2)} for item in records],
        "weighted_pivot + price_volume_decomposition",
        "贡献拆解是会计恒等近似，跨区域调拨与临时附加费需另列口径。",
    )



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
