PROJECT_KEY = "demand_forecast"
PROJECT_NAME = "生鲜需求预测室"
ENTITY_LABELS = [
  "销量序列",
  "门店资产",
  "预测方案",
  "回测任务",
  "审计记录",
  "复核意见"
]
ALGORITHM_LABELS = [
  "Holt-Winters 加性季节模型",
  "滚动回测 MAPE 评估"
]
ROLE_LABELS = {
    "admin": "数据管理员",
    "analyst": "分析员",
    "reviewer": "业务复核员",
}
