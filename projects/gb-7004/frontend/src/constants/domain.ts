export const PROJECT_NAME = "检验分布漂移台";
export const CLIENT_NAME = "澄明医学检验所（9 个实验室）";
export const ENTITY_LABELS = [
  "质控片段",
  "实验室资产",
  "漂移方案",
  "监测任务",
  "审计记录",
  "复核意见"
] as const;
export const PAGE_LABELS = [
  "漂移雷达",
  "质控资产",
  "监测编排",
  "分布对比结果",
  "治理审计"
] as const;
export const ALGORITHM_LABELS = [
  "Kolmogorov-Smirnov 分布检验",
  "Population Stability Index 分箱漂移"
] as const;
