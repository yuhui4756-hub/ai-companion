import type { ModelProviderConfig, OpenAIChatMessage } from "../types";

export type ModelErrorCode =
  | "missing-config"
  | "auth"
  | "quota"
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
    .replace(/([?&](?:api[_-]?key|access[_-]?token|token|key|secret)=)[^&#\s]+/gi, "$1[已隐藏]")
    .replace(/sk-[A-Za-z0-9_-]{8,}/g, "[已隐藏 API Key]")
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]{8,}/gi, "Bearer [已隐藏]")
    .replace(
      /(api[_-]?key|x-api-key|authorization|access[_-]?token|token|secret)(\s*[:=]\s*)["']?[^"'\s,;，；}]+["']?/gi,
      "$1$2[已隐藏]",
    )
    .replace(/\b[A-Za-z0-9._~+/=-]{32,}\b/g, "[已隐藏疑似密钥]")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 160);
}

function serviceDetail(message?: string): string {
  if (!message) return "服务没有给出详细原因。";
  const safeMessage = sanitizeServiceMessage(message);
  return safeMessage ? `服务返回：${safeMessage}` : "服务返回了错误，但详情已隐藏。";
}

export function validateProviderConfig(config: ModelProviderConfig): void {
  const missingFields = [
    !config.baseURL.trim() ? "baseURL" : "",
    !config.model.trim() ? "model" : "",
    !config.apiKey.trim() ? "API Key" : "",
  ].filter(Boolean);
  if (missingFields.length > 0) {
    throw new ModelProviderError("missing-config", `请先在设置里填写 ${missingFields.join("、")}。`);
  }
}

export async function requestDirectChatCompletion(
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
    throw new ModelProviderError(
      "network",
      "网络请求失败。请检查接口地址、网络连接或代理；如果浏览器无法直接访问该接口，也可能是服务商跨域限制。",
    );
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
    if (response.status === 402 || response.status === 429) {
      throw new ModelProviderError("quota", `额度、余额或频率限制可能不足，请检查服务商账户权限。${detail}`);
    }
    if (response.status === 404) {
      throw new ModelProviderError("model", `接口地址或模型名可能不正确，请检查 baseURL 和 model。${detail}`);
    }
    if (response.status === 400) {
      throw new ModelProviderError("model", `模型请求参数不被服务商接受，请检查 model 是否可用。${detail}`);
    }
    throw new ModelProviderError("model", `模型请求失败，状态码 ${response.status}。${detail}`);
  }

  const content = data.choices?.[0]?.message?.content;
  if (!content) {
    throw new ModelProviderError("invalid-response", "模型响应格式异常，没有拿到 assistant 内容。");
  }

  return content;
}

export const requestChatCompletion = requestDirectChatCompletion;
