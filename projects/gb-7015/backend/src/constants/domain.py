PROJECT_KEY = "anomaly_review"
PROJECT_NAME = "交易异常复核台"
ENTITY_LABELS = [
  "交易样本",
  "商户资产",
  "检测方案",
  "复核任务",
  "审计记录",
  "复核意见"
]
ALGORITHM_LABELS = [
  "Isolation Forest 无监督异常分",
  "稳健 z-score 信号解释"
]
ROLE_LABELS = {
    "admin": "数据管理员",
    "analyst": "分析员",
    "reviewer": "业务复核员",
}
