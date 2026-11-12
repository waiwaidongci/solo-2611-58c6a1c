import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1008)
    rows = []
    for index in range(3000):
        f1 = rng.normal()
        f2 = rng.normal()
        f3 = .87 * f1 + rng.normal(0, .4)
        f4 = rng.normal()
        f5 = rng.normal()
        signal = 1.15 * f1 - .72 * f2 + .18 * f4 + rng.normal(0, .7)
        rows.append({"device_id": f"D{index:05d}", "f_1": round(float(f1), 5),
                     "f_2": round(float(f2), 5), "f_3": round(float(f3), 5),
                     "f_4": round(float(f4), 5), "f_5": round(float(f5), 5),
                     "label": int(signal > 0)})
    return rows

