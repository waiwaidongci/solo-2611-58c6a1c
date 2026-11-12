import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1015)
    rows = []
    for index in range(3200):
        anomalous = index % 63 == 0
        amount = float(rng.lognormal(8.1, .7))
        hour = int(rng.integers(0, 6))
        velocity = float(rng.normal(1.2, .4))
        if anomalous:
            amount *= rng.uniform(5, 12)
            velocity *= rng.uniform(3, 7)
        rows.append({"id": f"TX{index:06d}", "merchant": f"M{index % 480:04d}",
                     "amount": round(amount, 2), "hour": hour,
                     "velocity": round(max(0, velocity), 4)})
    return rows

