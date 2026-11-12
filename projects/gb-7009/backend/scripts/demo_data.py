import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1009)
    rows = []
    for index in range(2800):
        latent = rng.normal()
        y = int(latent + rng.normal(0, .9) > .25)
        p_base = 1 / (1 + np.exp(-(.75 * latent + rng.normal(0, 1.1))))
        p_tree = 1 / (1 + np.exp(-(1.05 * latent + rng.normal(0, .8))))
        p_logit = 1 / (1 + np.exp(-(.92 * latent + rng.normal(0, .95))))
        rows.append({"id": f"E{index:05d}", "y": y,
                     "p_base": round(float(p_base), 6), "p_tree": round(float(p_tree), 6),
                     "p_logit": round(float(p_logit), 6)})
    return rows

