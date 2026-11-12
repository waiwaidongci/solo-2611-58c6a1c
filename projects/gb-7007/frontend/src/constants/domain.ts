export const PROJECT_NAME = "订阅流失预警台";
export const CLIENT_NAME = "弦桥云服务（B2B SaaS）";
export const ENTITY_LABELS = [
  "账户样本",
  "客户资产",
  "预警方案",
  "评分任务",
  "审计记录",
  "复核意见"
] as const;
export const PAGE_LABELS = [
  "流失雷达",
  "账户资产",
  "模型编排",
  "风险清单",
  "治理审计"
] as const;
export const ALGORITHM_LABELS = [
  "带类别权重的 Logistic Regression",
  "ROC AUC 与 Bootstrap 置信区间"
] as const;
