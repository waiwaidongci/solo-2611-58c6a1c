import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1017)
    rows = []
    steps = [("进入开户", 10000, 0), ("身份认证", 8400, 1), ("活体检测", 7050, 2),
             ("绑定银行卡", 5020, 3), ("首笔转入", 4180, 4), ("完成激活", 3960, 5)]
    for channel in ["自然流量", "投放", "合作渠道"]:
        for step, users, seq in steps:
            adjusted = int(users * (1.0 if channel == "自然流量" else .76 if channel == "投放" else .52))
            adjusted = int(adjusted * rng.uniform(.98, 1.02))
            rows.append({"step": step, "users": adjusted, "seq": seq, "channel": channel})
    return rows

