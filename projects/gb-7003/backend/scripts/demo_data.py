import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1003)
    rows = []
    effects = {"A-习惯": 0, "B-深播": .42, "C-膜下滴灌": .73, "D-减氮": -.18, "E-晚播": -.51}
    for index in range(4200):
        batch = list(effects)[index % 5]
        value = 7.4 + effects[batch] + rng.normal(0, 1.15)
        rows.append({"batch": batch, "value": round(float(value), 4),
                     "field": f"F{index % 31:02d}", "season": 2026})
    return rows

