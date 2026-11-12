import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1020)
    rows = []
    lines = {"A线": 4.2, "B线": 4.31, "C线": 4.16, "D线": 4.49, "E线": 4.25}
    for index in range(2200):
        line = list(lines)[index % 5]
        value = np.random.default_rng(1020 + index).normal(lines[line], .38)
        rows.append({"line": line, "batch": f"B{index // 5 % 3 + 1}", "value": round(float(value), 4),
                     "metric": "含水率"})
    return rows

