import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1019)
    rows = []
    for index in range(2200):
        age = str(rng.choice(["18-29", "30-44", "45-59", "60+"], p=[.38, .39, .17, .06]))
        education = str(rng.choice(["高中及以下", "大专", "本科", "研究生"], p=[.18, .25, .43, .14]))
        rows.append({"respondent": f"R{index:05d}", "age_group": age, "education": education,
                     "region": ["中心", "近郊", "远郊"][index % 3],
                     "mode": "公交" if index % 4 else "自驾", "base_weight": 1.0})
    return rows

