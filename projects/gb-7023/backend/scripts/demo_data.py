import math

import numpy as np



def demo_rows():
    rng = np.random.default_rng(1023)
    templates = [
        "司机绕路 路线 偏航 导航 不准", "车内异味 清洁 座椅 卫生", "司机态度 冷漠 催促 沟通 差",
        "等待太久 接驾 慢 排队 时间", "费用异常 附加费 扣款 账单 不明", "定位不准 上车点 找不到 地图",
        "司机取消 订单 取消 频繁 接单", "发票 无法 开具 行程 报销 问题",
    ]
    rows = []
    for index in range(1600):
        template = templates[index % len(templates)]
        words = template.split()
        text = "".join(str(rng.choice(words)) + "，" for _ in range(int(rng.integers(3, 7))))
        rows.append({"ticket_id": f"T{index:05d}", "text": text.rstrip("，"),
                     "business": ["快车", "专车", "顺风"][index % 3],
                     "city": ["上海", "杭州", "南京"][index % 3]})
    return rows

