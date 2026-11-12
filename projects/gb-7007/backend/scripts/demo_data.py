import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1007)
    rows = []
    for index in range(3200):
        tenure = float(rng.integers(2, 48))
        usage = float(max(0, rng.normal(21, 8)))
        tickets = float(rng.poisson(1.4))
        gap = float(max(0, rng.normal(9, 7)))
        logit = -.08 * tenure - .11 * usage + .45 * tickets + .16 * gap - 1.9
        probability = 1 / (1 + math.exp(-logit))
        rows.append({"account_id": f"AC{index:05d}", "tenure": tenure,
                     "usage": round(usage, 2), "tickets": tickets,
                     "login_gap": round(gap, 2), "churned": int(rng.random() < probability)})
    return rows

