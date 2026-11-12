export const PROJECT_NAME = "生鲜需求预测室";
export const CLIENT_NAME = "青禾生鲜（64 家社区店）";
export const ENTITY_LABELS = [
  "销量序列",
  "门店资产",
  "预测方案",
  "回测任务",
  "审计记录",
  "复核意见"
] as const;
export const PAGE_LABELS = [
  "需求预测",
  "销量资产",
  "预测编排",
  "七天回测",
  "治理审计"
] as const;
export const ALGORITHM_LABELS = [
  "Holt-Winters 加性季节模型",
  "滚动回测 MAPE 评估"
] as const;
