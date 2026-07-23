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

## 工程化升级阶段蓝图

当前项目已经完成本地网页和 Electron 桌面版基础能力。下一阶段重点不是推翻现有前端，而是在保持本地优先的前提下增加工程层。为兼顾实际价值和简历表达，第二轮优先评估 Python/FastAPI 本地服务，让项目形成“React/Electron 客户端 + Python 本地后端”的清晰架构。

1. 本地后端代理
   - 第一轮已先落地 Electron 主进程代理，解决桌面端密钥边界和错误脱敏。
   - 第二轮优先评估 Python/FastAPI 本地服务，统一承接模型请求、数据访问和 RAG 检索；Electron 可负责启动/连接本地服务，Web 调试版保留兼容路径。
   - 前端只调用本地代理接口或桌面桥，代理负责拼接供应商 `baseURL`、鉴权、错误归一化和后续流式响应。
   - 第一版代理仍使用用户自己的 API Key，不代管商业 Key，不上传到远端。
   - 代理要保留清晰错误码：缺少配置、认证失败、余额/频率不足、网络失败、模型不可用、响应异常。

2. SQLite 本地持久化
   - 优先评估由 Python 服务管理 SQLite，作为桌面版稳定存储；Web 调试版可以继续保留 `localStorage` 兼容层。
   - 建议把数据访问收敛到 repository/service 层，避免 UI 直接依赖具体存储实现。
   - 迁移顺序：先读旧 `localStorage`，导入到新库，校验后保留可回退导出能力。
   - 最小表：companions、messages、memories、style_summaries、provider_configs、knowledge_sources、knowledge_chunks。

3. 本地知识库/RAG
   - 第一版只支持用户手动导入文本或 Markdown，不做联网爬取。
   - 导入文本在 Python 本地服务中切分为 chunks，保存来源、标题、时间和摘要。
   - 检索可以先用 Python 实现简单关键词/模糊匹配，架构上预留 embedding 向量字段。
   - prompt 注入时必须标记为“用户导入资料”，不能把知识库片段当成长期记忆或模型事实。

## 建议实施顺序

1. 保留第一轮 Electron 主进程代理和 repository/RAG 骨架，确认不倒退已通过的安全边界。
2. 新增最小 Python/FastAPI 本地服务骨架，优先暴露健康检查、模型代理或数据访问中的一个可运行接口。
3. 引入 SQLite 并完成伴侣、消息、记忆、风格摘要的最小读写或迁移验证。
4. 做最小知识库导入、切分、检索和 prompt 注入，优先复用 Python 服务承接 RAG 逻辑。
5. 补齐迁移、错误处理、无密钥泄漏、启动说明和回归测试。

## 风险边界

- 不在文档、日志、公开讨论或仓库中记录真实 API Key。
- 不自动同步用户聊天记录、长期记忆或知识库内容。
- 如果引入第三方 embedding 或云端向量服务，必须先确认隐私、费用和数据保留风险。
- 如果涉及 QQ/微信、模型价格或供应商限制，必须实时查证官方资料。
