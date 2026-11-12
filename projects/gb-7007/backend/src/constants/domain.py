PROJECT_KEY = "churn_model"
PROJECT_NAME = "订阅流失预警台"
ENTITY_LABELS = [
  "账户样本",
  "客户资产",
  "预警方案",
  "评分任务",
  "审计记录",
  "复核意见"
]
ALGORITHM_LABELS = [
  "带类别权重的 Logistic Regression",
  "ROC AUC 与 Bootstrap 置信区间"
]
ROLE_LABELS = {
    "admin": "数据管理员",
    "analyst": "分析员",
    "reviewer": "业务复核员",
}
