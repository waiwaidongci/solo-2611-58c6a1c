import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1011)
    regions = ["沪苏", "浙皖", "闽赣", "鲁豫", "湘鄂", "川渝", "京津冀", "粤港澳"]
    rows = []
    for index in range(4000):
        region = regions[index % len(regions)]
        period = "base" if index % 2 == 0 else "current"
        orders = int(rng.integers(80, 210))
        price = 730 + regions.index(region) * 27 + rng.normal(0, 18)
        if period == "current":
            orders = int(orders * rng.uniform(.91, 1.12))
            price *= rng.uniform(1.01, 1.07)
        rows.append({"region": region, "period": period, "orders": orders,
                     "revenue": round(orders * price, 2),
                     "cost": round(orders * price * rng.uniform(.73, .87), 2),
                     "customer": f"C{index % 38:02d}"})
    return rows

