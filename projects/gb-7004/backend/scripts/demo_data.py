import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1004)
    rows = []
    for index in range(4800):
        period = "reference" if index % 2 == 0 else "current"
        value = rng.normal(5.3, .44) if period == "reference" else rng.normal(5.55, .61)
        rows.append({"period": period, "value": round(float(value), 4),
                     "lab": f"LAB-{index % 9 + 1}", "reagent": "R2409" if period == "reference" else "R2410"})
    return rows

