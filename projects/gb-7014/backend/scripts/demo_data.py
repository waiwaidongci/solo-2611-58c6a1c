import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1014)
    rows = []
    for store in range(4):
        for index in range(120):
            weekday = index % 7
            demand = 135 + index * .26 + (24 if weekday in (5, 6) else 0) + rng.normal(0, 9)
            rows.append({"date": f"2026-{7 + index // 30:02d}-{index % 30 + 1:02d}",
                         "demand": max(50, round(float(demand))), "store": f"Q{store + 1}",
                         "sku": "有机生菜" if store % 2 == 0 else "低温鲜奶"})
    return rows

