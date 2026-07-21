# 项目总控上下文

## 一句话定位

AI伴侣/所依是一个本地优先的中文 BYOK AI 恋爱伴侣应用，包含 Web 调试入口与 Windows Electron 桌面入口，支持用户自填 API Key、多伴侣人格选择、长期记忆和情绪价值回应。

## 用户目标

- 自己和朋友可以使用。
- 未来可以作为简历项目展示 AI 应用开发能力。
- 项目要尽量完整，而不是只有一个简单聊天页面。
- 技术问题由 Codex 主动判断和解决，必要时只向用户索要权限、登录或高风险确认。

## 产品原则

- 陪伴优先：先理解和回应情绪，再解决问题。
- 真实自然：默认像一个稳定、有温度的人，而不是客服或模板机器人。
- 用户可控：伴侣类型、聊天风格、API Key、长期记忆都应尽量由用户掌控。
- 隐私优先：API Key、聊天记录、长期记忆默认本地保存，后续如需云端同步再单独设计。
- 可扩展：网页是第一个入口，未来 QQ、微信只是新的入口适配层。

## 历史 MVP 默认决定

- 第一版做中文网页 Demo；当前项目已经扩展到 Electron 桌面版。
- 第一版不做复杂注册登录。
- 第一版支持预设伴侣和轻量自定义，不做完整角色市场。
- 第一版支持用户自填 API Key。
- 第一版至少支持一种 OpenAI 兼容接口，技术结构预留多模型供应商。
- 第一版实现长期记忆的查看、编辑、删除。
- 第一版不直接接入 QQ/微信，但代码架构保留入口适配层。

## 待后续查证

- 微信个人号、公众号、企业微信、微信开放平台的可行接入路径和限制。
- QQ 机器人或频道机器人相关接入路径和限制。
- 各主流模型供应商 API 的最新接口格式、可用模型、价格和密钥安全建议。

## 当前实现状态（2026-07-21）

- 项目已经从网页 Demo 发展为本地优先的中文 BYOK AI 恋爱伴侣应用，并已有 Windows Electron 安装包。
- 当前核心仍以前端/Electron 应用为主；桌面端已加入 Electron 主进程模型代理，Web 调试入口保留浏览器直连用户配置模型服务的兼容路径。
- API Key 默认仍保存在当前浏览器或 Electron 应用本地的 `localStorage`；Python 后端不接收、不保存、不转发模型 API Key，SQLite 里的 provider 配置只保存去 Key 字段和 `renderer-localStorage` 引用。
- 已有长期记忆、风格摘要、伴侣模板、提示词边界、导入导出、桌面更新源、OneBot 本地实验骨架、repository/RAG 边界骨架和 Python/FastAPI 本地后端。
- 工程化 2A 已完成知识库/RAG 切片：知识库资料可写入本机 SQLite，支持导入文本/Markdown、切分、检索、prompt context 生成和软删除后不再注入。
- 工程化 2B 已完成核心数据 SQLite 迁移与 Electron dev sidecar 切片：后端 schema v2 支持 core snapshot、legacy `localStorage` snapshot 幂等事务导入、companions/messages/memories/style_summaries/provider_configs 读写；Electron 开发态可托管 Python sidecar、端口回退并在退出时清理。
- 工程化 2C 已完成本地候选打包切片：`npm run desktop:dist` 会先用 PyInstaller 构建 `suoyi-backend.exe`，再通过 `electron-builder` 把 Python sidecar 资源放入桌面候选包；packaged smoke 已验证 sidecar 启动、端口回退、缺失资源 fallback、退出清理、2A/2B API 回归。
- 当前公开发布版本仍是 `0.1.1`，本轮没有 bump version、没有上传 GitHub Release、没有触发自动更新；正式发布、升级路径、回滚和 SmartScreen/代码签名说明留到发布前确认。

## 工程化升级阶段目标

- 目标不是重做项目，而是在现有所依应用上补足 AI 应用开发项目的工程深度。
- 继续完善本地后端代理：统一模型请求、避免浏览器跨域问题、减少前端直接持有 Key 的暴露面，并为后续多供应商适配留接口。
- 继续升级数据持久化：在已完成 core snapshot/迁移基础上，推进更细粒度 CRUD、恢复/清理 UI、发布打包和升级回滚。
- 继续完善最小 RAG/知识库能力：用户可导入自己明确授权使用的文本资料，系统本地切分、索引、检索，并把相关片段注入对话。
- 简历表达重点：React/Electron 客户端、Python/FastAPI 本地后端、本地优先隐私设计、多模型兼容、本地代理、SQLite、数据迁移、长期记忆、RAG 检索增强、桌面应用交付。

## 本阶段非目标

- 不做云账号、云同步、付费系统或公开角色市场。
- 不把用户 API Key、聊天记录、长期记忆或导入资料上传到自有服务器。
- 不把 QQ/微信真实接入作为本阶段交付目标；平台规则仍需实时查证。
- 不追求复杂企业级后端，优先做能跑通、能解释、可验证的小型本地工程闭环。
