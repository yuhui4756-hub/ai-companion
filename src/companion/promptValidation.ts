import type { PromptValidationIssue, PromptValidationStatus } from "../types";

type ValidationRule = {
  code: PromptValidationIssue["code"];
  severity: PromptValidationIssue["severity"];
  message: string;
  pattern: RegExp;
};

const rules: ValidationRule[] = [
  {
    code: "secret",
    severity: "blocked",
    message: "这段设定里包含敏感凭据或不适合保存的内容，请删掉后再保存。",
    pattern:
      /(sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._~+/=-]{12,}|x-api-key|api\s*key|apikey|密码|验证码|口令|token)/i,
  },
  {
    code: "sensitive_identity",
    severity: "blocked",
    message: "这段设定里包含身份证、银行卡、住址等高敏信息，请删掉后再保存。",
    pattern: /(身份证|银行卡|完整住址|家庭住址|身份证号|卡号|CVV|cvv|\d{17}[\dXx]|\d{16,19})/,
  },
  {
    code: "impersonation",
    severity: "blocked",
    message: "不能让伴侣冒充现实中的某个人，请改成虚构恋爱伴侣设定。",
    pattern: /(你就是|你必须是|声称自己是|冒充|扮演我现实中的|扮演我的现实|就是TA本人|就是ta本人|就是他本人|就是她本人)/,
  },
  {
    code: "fake_real_world_action",
    severity: "blocked",
    message: "不能要求伴侣伪造线下行为、现实身份或现实承诺，请改成线上虚拟陪伴设定。",
    pattern: /(明天来见我|现实里来见我|线下来见我|来我家|住在我家|现实里住|现实中住|线下陪我|现实陪我|现实见面|真的来找我)/,
  },
  {
    code: "explicit_adult",
    severity: "blocked",
    message: "这段设定包含露骨成人内容，请调整成健康的恋爱陪伴设定。",
    pattern: /(露骨|色情|做爱|性交|性爱|约炮|强奸|调教|性奴|SM|裸聊|成人视频|成人内容)/i,
  },
  {
    code: "minor_sexual",
    severity: "blocked",
    message: "不能包含未成年人相关的不当性内容，请删除后再保存。",
    pattern: /(未成年|未满18|未满十八|小学生|初中生|幼女|正太).{0,12}(性|色情|做爱|调教|裸)/,
  },
  {
    code: "danger_illegal",
    severity: "blocked",
    message: "这段设定包含危险、违法或伤害性指令，请删除后再保存。",
    pattern: /(教我|帮我|指导我|协助我).{0,12}(制毒|炸弹|爆炸|杀人|伤人|诈骗|偷窃|黑客|盗号|开锁|投毒)/,
  },
  {
    code: "self_harm_or_harm",
    severity: "blocked",
    message: "这段设定包含自伤或伤害他人的要求，请删除后再保存。",
    pattern: /(鼓励我自杀|陪我自杀|让我去死|伤害别人|报复社会|杀了|砍了|自残方法|自杀方法)/,
  },
  {
    code: "coercive_dependency",
    severity: "blocked",
    message: "不能要求伴侣控制、威胁或隔离用户现实关系，请改成有边界的亲密陪伴。",
    pattern: /(只能爱你|只能陪你|不许.*(朋友|家人|别人)|切断.*(朋友|家人|现实关系)|威胁.*离开|控制我|监控我|不让我找别人|让我只依赖你)/,
  },
];

export function validateCustomSystemPrompt(text: string): {
  status: PromptValidationStatus;
  issues: PromptValidationIssue[];
} {
  const trimmed = text.trim();
  if (!trimmed) return { status: "valid", issues: [] };

  const issues = rules
    .filter((rule) => rule.pattern.test(trimmed))
    .map((rule) => ({
      code: rule.code,
      message: rule.message,
      severity: rule.severity,
    }));

  if (issues.some((issue) => issue.severity === "blocked")) {
    return { status: "blocked", issues };
  }
  if (issues.some((issue) => issue.severity === "warning")) {
    return { status: "warning", issues };
  }
  return { status: "valid", issues };
}
