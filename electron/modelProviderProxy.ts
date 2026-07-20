import { ipcMain } from "electron";

type ModelErrorCode =
  | "missing-config"
  | "auth"
  | "quota"
  | "network"
  | "model"
  | "invalid-response";

type ModelProviderConfig = {
  providerName: string;
  baseURL: string;
  apiKey: string;
  model: string;
};

type OpenAIChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

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

type ModelProviderProxyResponse =
  | {
      ok: true;
      content: string;
    }
  | {
      ok: false;
      error: {
        code: ModelErrorCode;
        message: string;
      };
    };

class ModelProviderProxyError extends Error {
  code: ModelErrorCode;

  constructor(code: ModelErrorCode, message: string) {
    super(message);
    this.name = "ModelProviderProxyError";
    this.code = code;
  }
}

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

function validateProviderConfig(config: ModelProviderConfig): void {
  const missingFields = [
    !config.baseURL.trim() ? "baseURL" : "",
    !config.model.trim() ? "model" : "",
    !config.apiKey.trim() ? "API Key" : "",
  ].filter(Boolean);
  if (missingFields.length > 0) {
    throw new ModelProviderProxyError("missing-config", `请先在设置里填写 ${missingFields.join("、")}。`);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object";
}

function readString(source: Record<string, unknown>, field: string): string {
  const value = source[field];
  return typeof value === "string" ? value : "";
}

function parseProviderConfig(value: unknown): ModelProviderConfig {
  if (!isRecord(value)) {
    return {
      providerName: "",
      baseURL: "",
      apiKey: "",
      model: "",
    };
  }

  return {
    providerName: readString(value, "providerName"),
    baseURL: readString(value, "baseURL"),
    apiKey: readString(value, "apiKey"),
    model: readString(value, "model"),
  };
}

function parseMessages(value: unknown): OpenAIChatMessage[] {
  if (!Array.isArray(value)) {
    throw new ModelProviderProxyError("invalid-response", "模型请求参数格式异常。");
  }

  return value.map((message) => {
    if (!isRecord(message)) {
      throw new ModelProviderProxyError("invalid-response", "模型请求参数格式异常。");
    }
    const role = message.role;
    const content = message.content;
    if (
      (role !== "system" && role !== "user" && role !== "assistant") ||
      typeof content !== "string"
    ) {
      throw new ModelProviderProxyError("invalid-response", "模型请求参数格式异常。");
    }
    return { role, content };
  });
}

function parseRequestPayload(payload: unknown): {
  config: ModelProviderConfig;
  messages: OpenAIChatMessage[];
} {
  if (!isRecord(payload)) {
    throw new ModelProviderProxyError("invalid-response", "模型请求参数格式异常。");
  }

  return {
    config: parseProviderConfig(payload.config),
    messages: parseMessages(payload.messages),
  };
}

async function requestProxiedChatCompletion(
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
    throw new ModelProviderProxyError(
      "network",
      "网络请求失败。请检查接口地址、网络连接或代理；桌面版本机代理无法连接到模型服务商。",
    );
  }

  let data: OpenAIChatCompletionResponse;
  try {
    data = (await response.json()) as OpenAIChatCompletionResponse;
  } catch {
    throw new ModelProviderProxyError("invalid-response", "模型服务返回了无法解析的响应。");
  }

  if (!response.ok) {
    const detail = serviceDetail(data.error?.message);
    if (response.status === 401 || response.status === 403) {
      throw new ModelProviderProxyError("auth", `认证失败，请检查 API Key 是否正确。${detail}`);
    }
    if (response.status === 402 || response.status === 429) {
      throw new ModelProviderProxyError("quota", `额度、余额或频率限制可能不足，请检查服务商账户权限。${detail}`);
    }
    if (response.status === 404) {
      throw new ModelProviderProxyError("model", `接口地址或模型名可能不正确，请检查 baseURL 和 model。${detail}`);
    }
    if (response.status === 400) {
      throw new ModelProviderProxyError("model", `模型请求参数不被服务商接受，请检查 model 是否可用。${detail}`);
    }
    throw new ModelProviderProxyError("model", `模型请求失败，状态码 ${response.status}。${detail}`);
  }

  const content = data.choices?.[0]?.message?.content;
  if (!content) {
    throw new ModelProviderProxyError("invalid-response", "模型响应格式异常，没有拿到 assistant 内容。");
  }

  return content;
}

export function registerModelProviderIpc(): void {
  ipcMain.handle(
    "model-provider:request-chat-completion",
    async (_event, payload: unknown): Promise<ModelProviderProxyResponse> => {
      try {
        const { config, messages } = parseRequestPayload(payload);
        const content = await requestProxiedChatCompletion(config, messages);
        return { ok: true, content };
      } catch (error) {
        if (error instanceof ModelProviderProxyError) {
          return {
            ok: false,
            error: {
              code: error.code,
              message: error.message,
            },
          };
        }
        return {
          ok: false,
          error: {
            code: "model",
            message: "模型代理请求失败，请稍后重试。",
          },
        };
      }
    },
  );
}
