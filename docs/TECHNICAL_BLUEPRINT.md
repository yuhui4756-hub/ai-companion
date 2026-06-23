# 技术蓝图

## 架构目标

第一版做本地网页 Demo，但代码结构按未来可扩展到 QQ、微信等入口来设计。

## 建议技术栈

- 前端：React + TypeScript + Vite
- 样式：普通 CSS 或轻量 Tailwind，优先清晰稳定
- 本地存储：浏览器 localStorage 或 IndexedDB
- API 调用：前端直连用户配置的 OpenAI 兼容接口，后续可加本地后端代理
- 测试：基础单元测试 + 浏览器手动验收

## 核心模块

| 模块 | 说明 |
| --- | --- |
| companion | 伴侣人设、类型、提示词片段 |
| memory | 长期记忆的增删改查、记忆分类 |
| model-provider | API供应商配置、OpenAI兼容接口适配 |
| chat-engine | 组装系统提示词、历史消息、长期记忆并发起模型请求 |
| storage | 本地持久化配置、聊天记录、记忆 |
| ui | 设置页、聊天页、记忆管理页 |
| channel-adapter | 入口适配层，第一版只有 Web，未来扩展 QQ/微信 |

## BYOK 设计

BYOK 指用户自带 API Key。第一版原则：

- 项目不内置任何商业 API Key。
- API Key 默认只存用户本机。
- 设置页需要明确提示用户风险。
- 配置支持自定义 baseURL、model、apiKey。
- 优先支持 OpenAI 兼容接口，降低多供应商适配成本。

## 数据模型草案

```ts
type CompanionProfile = {
  id: string;
  name: string;
  type: "friend" | "romantic" | "rational" | "healing" | "roleplay";
  tone: string;
  boundaries: string[];
};

type UserMemory = {
  id: string;
  category: "basic" | "preference" | "event" | "emotion" | "relationship" | "boundary";
  content: string;
  importance: 1 | 2 | 3;
  createdAt: string;
  updatedAt: string;
};

type ModelProviderConfig = {
  providerName: string;
  baseURL: string;
  apiKey: string;
  model: string;
};
```

## 未来 QQ/微信接入预留

未来入口不直接影响核心聊天逻辑，只新增 channel adapter：

- WebAdapter：网页输入输出。
- QQAdapter：QQ 消息转为统一 ChatMessage。
- WeChatAdapter：微信消息转为统一 ChatMessage。

核心 chat-engine 不关心消息来自哪里。
