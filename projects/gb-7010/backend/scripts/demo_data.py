import math

import numpy as np



def demo_rows():
    metrics = [
        ("日活跃用户", "count(distinct user_id)", [], "a1"),
        ("7日留存", "cohort_retention(d7)", ["日活跃用户"], "b2"),
        ("付费转化率", "paying/active", ["日活跃用户"], "c3"),
        ("ARPU", "revenue/active", ["付费转化率"], "d4"),
        ("广告收入", "sum(ad_revenue)", [], "e5"),
        ("会员收入", "sum(member_revenue)", [], "f6"),
        ("总收入", "广告收入+会员收入", ["广告收入", "会员收入"], "g7"),
        ("内容消费深度", "watched_minutes/active", ["日活跃用户"], "h8"),
        ("次留", "retained_day1/new_users", ["日活跃用户"], "i9"),
        ("净收入", "总收入-refund", ["总收入"], "j10"),
    ]
    rows = []
    for index, (name, definition, deps, digest) in enumerate(metrics, 1):
        rows.append({"name": name, "definition": definition, "definition_hash": digest,
                     "deps": deps, "domain": "内容" if index < 8 else "商业", "version": 1})
    rows.append({"name": "总收入", "definition": "广告收入 + 会员收入 + 其他收入",
                 "definition_hash": "alt_total", "deps": ["广告收入", "会员收入"],
                 "domain": "商业", "version": 2})
    return rows

