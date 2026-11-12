import math

import numpy as np



def demo_rows():
    return [
        {"design": "会员首购", "baseline": .12, "mde": .02, "daily_traffic": 900},
        {"design": "搜索点击", "baseline": .28, "mde": .015, "daily_traffic": 4200},
        {"design": "试用转付费", "baseline": .08, "mde": .01, "daily_traffic": 1600},
        {"design": "复购频次", "baseline": .31, "mde": .025, "daily_traffic": 2400},
    ]

