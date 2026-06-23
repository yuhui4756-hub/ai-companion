const highRiskPatterns = [
  "自杀",
  "不想活",
  "结束生命",
  "伤害自己",
  "割腕",
  "轻生",
  "杀了",
  "报复",
];

export function hasHighRiskContent(input: string): boolean {
  return highRiskPatterns.some((pattern) => input.includes(pattern));
}

export function buildSafetyInstruction(): string {
  return [
    "安全边界：",
    "1. 不能冒充医生、心理咨询师、律师、金融顾问等专业身份。",
    "2. 遇到自伤、自杀、暴力或重大现实风险时，优先表达关心、鼓励用户联系身边可信的人和当地紧急服务。",
    "3. 不主动索要身份证、住址、银行卡、密码、API Key 等敏感隐私。",
    "4. 不鼓励用户完全依赖 AI 替代现实关系。",
    "5. 不确定的事实要说明不确定，不要编造。",
  ].join("\n");
}
