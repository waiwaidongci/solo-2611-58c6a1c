PROJECT_KEY = "topic_clusters"
PROJECT_NAME = "客诉主题聚类室"
ENTITY_LABELS = [
  "客诉文本",
  "业务线资产",
  "主题方案",
  "聚类任务",
  "审计记录",
  "复核意见"
]
ALGORITHM_LABELS = [
  "TF-IDF 文本向量化",
  "NMF 主题分解与轮廓评估"
]
ROLE_LABELS = {
    "admin": "数据管理员",
    "analyst": "分析员",
    "reviewer": "业务复核员",
}
