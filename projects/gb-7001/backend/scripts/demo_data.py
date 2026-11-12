import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1001)
    rows = []
    for index in range(4800):
        group = "A-对照" if index % 2 == 0 else "B-长醒发"
        rate = .112 if group.startswith("A") else .132
        rows.append({"user_id": f"m{index:05d}", "group": group, "exposure": 1,
                     "conversion": int(rng.random() < rate), "store": f"S{index % 42:02d}"})
    return rows

