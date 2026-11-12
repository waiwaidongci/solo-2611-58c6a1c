import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1012)
    regions = ["东区", "南区", "西区", "北区", "中心区", "近郊"]
    rows = []
    for index in range(1600):
        sent = int(rng.integers(30, 180))
        delivered = int(sent * rng.uniform(.92, .995))
        opened = int(delivered * rng.uniform(.38, .72))
        rows.append({"report_name": f"{regions[index % 6]}晨报", "region": regions[index % 6],
                     "sent": sent, "delivered": delivered, "opened": opened,
                     "cron": "0 7 * * 1-5", "batch": f"2026-11-{index % 13 + 1:02d}"})
    return rows

