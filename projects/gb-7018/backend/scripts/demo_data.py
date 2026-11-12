import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1018)
    rows = []
    lines = ["沪宁", "沪杭", "杭甬", "苏锡", "合宁", "甬台", "温福", "金义"]
    for index in range(3200):
        line = lines[index % len(lines)]
        base_price = 68 + lines.index(line) * 7
        price = max(20, base_price * rng.uniform(.86, 1.18))
        elasticity = -1.25 + lines.index(line) * .035
        units = 1000 * (price / base_price) ** elasticity * rng.lognormal(0, .08)
        rows.append({"line": line, "price": round(price, 2), "units": round(units, 2),
                     "period": "2026-W" + str(index % 32 + 1).zfill(2)})
    return rows

