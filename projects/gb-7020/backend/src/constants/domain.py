PROJECT_KEY = "batch_anova"
PROJECT_NAME = "批次质量分组台"
ENTITY_LABELS = [
  "检测样本",
  "产线资产",
  "比较方案",
  "分析任务",
  "审计记录",
  "复核意见"
]
ALGORITHM_LABELS = [
  "单因素 ANOVA",
  "Tukey 成对均值差与区间"
]
ROLE_LABELS = {
    "admin": "数据管理员",
    "analyst": "分析员",
    "reviewer": "业务复核员",
}
