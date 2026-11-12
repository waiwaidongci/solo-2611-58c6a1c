import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1024)
    centers = [(31.2304, 121.4737), (31.220, 121.52), (31.19, 121.43), (31.27, 121.47)]
    rows = []
    for index in range(4200):
        if index % 41 == 0:
            lat = 31.15 + rng.uniform(0, .22)
            lng = 121.30 + rng.uniform(0, .28)
        else:
            center = centers[index % len(centers)]
            lat = center[0] + rng.normal(0, .007)
            lng = center[1] + rng.normal(0, .009)
        rows.append({"order_id": f"O{index:06d}", "lat": round(float(lat), 6),
                     "lng": round(float(lng), 6), "amount": round(float(rng.lognormal(3.2, .5)), 2),
                     "station": f"ST{index % 18:02d}"})
    return rows

