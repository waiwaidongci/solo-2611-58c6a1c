export const PROJECT_NAME = "交易异常复核台";
export const CLIENT_NAME = "弦月支付（夜间风控组）";
export const ENTITY_LABELS = [
  "交易样本",
  "商户资产",
  "检测方案",
  "复核任务",
  "审计记录",
  "复核意见"
] as const;
export const PAGE_LABELS = [
  "夜间告警",
  "交易资产",
  "检测编排",
  "异常复核",
  "治理审计"
] as const;
export const ALGORITHM_LABELS = [
  "Isolation Forest 无监督异常分",
  "稳健 z-score 信号解释"
] as const;
