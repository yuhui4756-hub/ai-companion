import type { ModelProviderConfig, OpenAIChatMessage } from "../types";

export type ModelErrorCode =
  | "missing-config"
  | "auth"
  | "network"
  | "model"
  | "invalid-response";

export class ModelProviderError extends Error {
  code: ModelErrorCode;

  constructor(code: ModelErrorCode, message: string) {
    super(message);
    this.name = "ModelProviderError";
    this.code = code;
  }
}

type OpenAIChatCompletionResponse = {
  choices?: Array<{
    message?: {
      content?: string;
    };
  }>;
  error?: {
    message?: string;
  };
};

function normalizeBaseURL(baseURL: string): string {
  return baseURL.trim().replace(/\/+$/, "");
}

function sanitizeServiceMessage(message: string): string {
  return message
    .replace(/sk-[A-Za-z0-9_-]{8,}/g, "[已隐藏 API Key]")
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]{8,}/gi, "Bearer [已隐藏]")
    .replace(/(api[_-]?key|authorization|token|secret)(\s*[:=]\s*)[^\s,;，；]+/gi, "$1$2[已隐藏]")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 120);
}

function serviceDetail(message?: string): string {
  if (!message) return "服务没有给出详细原因。";
  const safeMessage = sanitizeServiceMessage(message);
  return safeMessage ? `服务返回：${safeMessage}` : "服务返回了错误，但详情已隐藏。";
}

export function validateProviderConfig(config: ModelProviderConfig): void {
  if (!config.baseURL.trim() || !config.model.trim() || !config.apiKey.trim()) {
    throw new ModelProviderError("missing-config", "请先在设置里填写 baseURL、model 和 API Key。");
  }
}

export async function requestChatCompletion(
  config: ModelProviderConfig,
  messages: OpenAIChatMessage[],
): Promise<string> {
  validateProviderConfig(config);

  let response: Response;
  try {
    response = await fetch(`${normalizeBaseURL(config.baseURL)}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify({
        model: config.model.trim(),
        messages,
        temperature: 0.8,
      }),
    });
  } catch {
    throw new ModelProviderError("network", "网络请求失败。请检查接口地址、网络连接，或浏览器是否被跨域限制拦住。");
  }

  let data: OpenAIChatCompletionResponse;
  try {
    data = (await response.json()) as OpenAIChatCompletionResponse;
  } catch {
    throw new ModelProviderError("invalid-response", "模型服务返回了无法解析的响应。");
  }

  if (!response.ok) {
    const detail = serviceDetail(data.error?.message);
    if (response.status === 401 || response.status === 403) {
      throw new ModelProviderError("auth", `认证失败，请检查 API Key 是否正确。${detail}`);
    }
    throw new ModelProviderError("model", `模型请求失败，状态码 ${response.status}。${detail}`);
  }

  const content = data.choices?.[0]?.message?.content;
  if (!content) {
    throw new ModelProviderError("invalid-response", "模型响应格式异常，没有拿到 assistant 内容。");
  }

  return content;
}
