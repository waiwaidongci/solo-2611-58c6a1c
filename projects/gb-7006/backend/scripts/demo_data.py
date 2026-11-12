import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1006)
    base = ["咖啡", "饭团", "面包", "牛奶", "茶叶蛋", "矿泉水", "关东煮", "口香糖"]
    rows = []
    for index in range(2200):
        items = list(rng.choice(base, size=int(rng.integers(1, 4)), replace=False))
        if "咖啡" in items and "面包" not in items and rng.random() < .58:
            items.append("面包")
        if "饭团" in items and "茶叶蛋" not in items and rng.random() < .46:
            items.append("茶叶蛋")
        rows.append({"basket_id": f"B{index:05d}", "items": items,
                     "store": f"N{index % 120:03d}", "hour": int(rng.integers(18, 24))})
    return rows

