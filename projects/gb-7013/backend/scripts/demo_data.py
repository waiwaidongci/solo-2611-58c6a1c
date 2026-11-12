import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1013)
    channels = ["开屏", "优惠券", "搜索", "私域", "内容种草"]
    rows = []
    for index in range(3000):
        path = []
        for _ in range(int(rng.integers(2, 6))):
            path.append(str(rng.choice(channels)))
        path = list(dict.fromkeys(path))
        conversion_probability = .10
        conversion_probability += .07 if "优惠券" in path else 0
        conversion_probability += .05 if "搜索" in path else 0
        rows.append({"path_id": f"P{index:05d}", "path": path,
                     "converted": int(rng.random() < conversion_probability),
                     "city": ["上海", "杭州", "南京"][index % 3]})
    return rows

