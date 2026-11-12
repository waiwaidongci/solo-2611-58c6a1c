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
    texts = [str(row.get("text", "")).strip() for row in rows if str(row.get("text", "")).strip()]
    if len(texts) < 20:
        raise ValueError("投诉文本不足")
    vectorizer = TfidfVectorizer(max_features=600, ngram_range=(1, 2), min_df=2)
    matrix = vectorizer.fit_transform(texts)
    topics = int(config.get("topics", 4))
    model = NMF(n_components=topics, init="nndsvda", random_state=42, max_iter=500)
    weights = model.fit_transform(matrix)
    labels = weights.argmax(axis=1)
    feature_names = vectorizer.get_feature_names_out()
    topic_records = []
    for topic in range(topics):
        indices = np.argsort(model.components_[topic])[::-1][:6]
        topic_records.append({"label": f"主题 {topic + 1}",
                              "keywords": [feature_names[index] for index in indices],
                              "size": int((labels == topic).sum())})
    sample_size = min(400, matrix.shape[0])
    silhouette = silhouette_score(matrix[:sample_size], labels[:sample_size]) if len(set(labels[:sample_size])) > 1 else 0
    topic_records.sort(key=lambda item: item["size"], reverse=True)
    return _envelope(
        f"归纳 {topics} 个客诉主题，最大主题 {topic_records[0]['size']} 条",
        f"TF-IDF + NMF 样本轮廓系数 {silhouette:.3f}；关键词由主题载荷最高的词组成。",
        [
            _metric("主题数", topics, "个", "neutral"),
            _metric("最大主题占比", topic_records[0]["size"] / len(texts) * 100, "%", "neutral"),
            _metric("轮廓系数", silhouette, "", "positive" if silhouette > .05 else "neutral"),
            _metric("文本量", len(texts), "条", "neutral"),
        ],
        [_series(item["label"], item["size"]) for item in topic_records],
        [{"label": item["label"], "keywords": ",".join(item["keywords"]), "size": item["size"]}
         for item in topic_records],
        "tfidf + nmf_topic_model",
        "主题词是归纳辅助，不应直接作为处罚依据；中文分词与否定语义仍是已知差异。",
    )



def run_algorithm(rows: list[dict], config: dict) -> dict:
    return run_primary(rows or [], config or {})
