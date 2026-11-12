PROJECT_KEY = "drift_monitor"
PROJECT_NAME = "检验分布漂移台"
ENTITY_LABELS = [
  "质控片段",
  "实验室资产",
  "漂移方案",
  "监测任务",
  "审计记录",
  "复核意见"
]
ALGORITHM_LABELS = [
  "Kolmogorov-Smirnov 分布检验",
  "Population Stability Index 分箱漂移"
]
ROLE_LABELS = {
    "admin": "数据管理员",
    "analyst": "分析员",
    "reviewer": "业务复核员",
}
