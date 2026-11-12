import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1021)
    rows = []
    for index in range(3400):
        latent = rng.normal()
        y = int(latent + rng.normal(0, .85) > .6)
        score = 1 / (1 + np.exp(-(1.1 * latent + rng.normal(0, .75))))
        rows.append({"application_id": f"AP{index:05d}", "y": y, "score": round(float(score), 6),
                     "product": ["现金分期", "消费贷"][index % 2]})
    return rows

