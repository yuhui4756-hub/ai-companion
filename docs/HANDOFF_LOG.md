# 阶段交接日志

本文件由总控维护，用来沉淀各专业线程的重要结论、当前状态和下一步任务。专业线程不直接修改本文件，只输出交接记录。

## 当前阶段索引（2026-07-20）

- 当前默认阶段：工程化升级阶段。
- 当前默认线程组：`AI伴侣-工程化-*`，线程 ID 见 `THREAD_REGISTRY.md` 的“工程化升级阶段线程（2026-07-20）”。
- 当前默认方向：本地后端代理、SQLite 或等价本地持久化、最小本地知识库/RAG、本地优先隐私边界。
- 旧 OneBot/NapCat、v0.1.1 Release、网页 Demo 初始化等记录均为历史阶段记录，除非总控明确复用，否则不作为本阶段默认交接对象。
- 后续回收线程时，按“来源线程/ID、完成内容、修改文件、验证、阻塞/普通/后续、下一步、任务包发送状态”记录。

## 2026-06-23 项目初始化

### 已完成

- 初始化本地 Git 仓库。
- 创建 GitHub 私有仓库：`https://github.com/yuhui4756-hub/ai-companion`
- 建立项目基础文档：`README.md`、`PROJECT_CONTEXT.md`、`THREAD_REGISTRY.md`、`TASK_HANDOFF.md`。
- 建立产品、AI人设、技术蓝图和验收文档。
- 创建 6 个专业线程：产品经理、AI人设设计、技术架构、开发实现、测试验收、记录交接。

### 产品经理结论

- 第一版核心不是普通聊天机器人，而是“情绪陪伴 + 长期记忆 + BYOK 多模型接入”的 AI 伴侣网页 Demo。
- P0 必须包含：伴侣类型选择、API Key/Base URL/Model 配置、OpenAI 兼容接口、本地长期记忆、记忆查看/编辑/删除、清晰错误提示。
- 第一版避免角色市场、复杂登录、QQ/微信真实接入，先把网页核心体验跑通。

### AI人设设计结论

- MVP 保留 5 类伴侣：温柔朋友、轻恋爱陪伴、理性支持、治愈陪伴、角色扮演。
- 默认首选“温柔朋友”，因为最稳、最符合基础陪伴定位，也最不容易踩边界。
- 所有伴侣共用基础回应规则：先判断意图，有情绪先接住，有问题再给可执行建议。
- 长期记忆应按相关性筛选后注入提示词，不要把全部记忆一次塞入模型。
- 高风险内容必须优先安全支持，不冒充医生、心理咨询师、律师或金融顾问。

### 技术架构结论

- 第一版采用本地单页 Web Demo，推荐 React + TypeScript + Vite。
- 第一版不先引入后端，BYOK 配置和长期记忆默认保存在用户本机。
- 核心模块建议拆为：`ui`、`companion`、`memory`、`model-provider`、`chat-engine`、`storage`、`channel-adapter`、`safety`。
- 模型请求先支持 OpenAI Chat Completions 兼容格式，未来再扩展供应商差异。
- QQ/微信入口只做架构预留，真实接入路径后续需要实时查证。

### 测试验收结论

- 验收按真实用户第一次使用顺序进行：选伴侣、填 API、聊天、管理记忆。
- 必测场景：不同伴侣风格差异、情绪倾诉、实际问题求助、记忆增删改查、错误 API 配置、安全边界、移动端适配。
- 删除记忆后必须通过实际对话确认已删除记忆不再被使用。
- 错误提示不能只显示原始技术报错，要转换成小白用户能理解的话。

### 记录交接结论

- 交接模板已经够用，但需要持续累计阶段日志。
- 专业线程不直接改登记表或日志，交由总控统一维护。

### 下一步

总控整合本日志后，正式交给开发实现线程开始搭建网页 Demo：

1. 初始化 React + TypeScript + Vite 工程。
2. 建立核心目录和类型。
3. 实现本地配置、伴侣选择、聊天引擎、OpenAI 兼容 API 调用。
4. 实现长期记忆查看、手动新增、编辑、删除。
5. 启动本地开发服务器，交给测试验收线程检查。

## 2026-06-23 开发交接回收

### 发现的问题

- 开发实现线程已经完成 Demo，但没有主动把结果推回总控。
- 这是流程机制问题，不是单个线程态度问题：背景线程只会在自己的线程里产出最终回复，总控需要主动读取。

### 修正规则

- 总控派发任务后必须记录线程 ID，并主动读取线程结果。
- 专业线程完成后必须在最终回复中写 `TASK_HANDOFF.md` 格式的交接记录。
- 专业线程完成后必须给出下一个线程的任务包，说明目标线程、背景、具体任务、不要做什么和验收标准。
- 总控读取后要把关键交接内容写入本日志，再决定验收、提交、推送或交给下一个线程。
- 如果专业线程没有交接，总控必须补写交接摘要，不允许让任务悬空。
- 开发产物必须先交给测试验收线程；总控不做中间验收。
- 测试验收失败时，总控按问题类型退回开发、人设、产品、架构或记录交接线程。
- 测试验收通过后，总控只做最终确认、提交和推送。

## 2026-06-23 协作流程完善

### 新增规则

- 新增 `docs/COLLABORATION_FLOW.md`，作为多线程协作总流程。
- 总控像项目负责人，只做用户沟通、大任务推进、交接回收、最终确认、提交推送。
- 专业线程各司其职，不插手其他线程职责。
- 专业线程完成后必须输出交接记录和“给下一个线程的任务包”。
- 目标明确且无用户决策/高风险操作时，专业线程可以直接把任务包发送给下一个登记线程；目标不明确或有风险时交回总控。
- 线程发送任务包后立即停止，不等待、不轮询、不追踪接收线程；总控也不死等过程，只在阶段节点回收结果。
- 返工必须按问题类型退回对应线程，并记录在阶段日志中。

### 本次开发线程交接摘要

- 已实现 React + TypeScript + Vite 单页 Demo。
- 已实现聊天、设置、记忆管理三个视图。
- 已实现 5 类伴侣预设、BYOK 配置、OpenAI Chat Completions 兼容调用、长期记忆 CRUD 和提示词注入。
- 已预留 Web/QQ/微信 channel adapter。
- 已运行 `npm install`、`npm run build`，并启动本地服务验证页面返回 200。

## 2026-06-23 测试复验与最终确认

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成返工后复验。
- 结论：通过中间验收，可交给总控做最终确认。
- 阻塞问题：无。

### 已通过项摘要

- `npm run build` 通过。
- 本地 `http://127.0.0.1:5173/` 可用。
- 桌面端 1280x720 和手机端 390x844 布局可用，无明显重叠或横向溢出。
- 设置页可保存 `baseURL`、`model`、`API Key`，侧边栏显示脱敏 Key。
- 缺少配置时提示清楚。
- 自动记忆沉淀可识别称呼和“不喜欢被催促”等明确偏好。
- 记忆可查看、删除；删除后不再进入长期记忆预览和 system prompt。
- 普通闲聊不会被自动保存为长期记忆。
- 源码搜索未发现真实硬编码 API Key。
- `src/model-provider/openai.ts` 已实现服务商错误详情脱敏与截断。

### 普通问题

- 删除长期记忆不等于删除聊天历史；聊天历史中仍可能保留用户原始消息。后续需要在隐私说明或数据管理设计中明确区分。
- 真实合法 JSON 的认证失败详情脱敏，建议有真实兼容服务后再抽测。

### 可后续优化

- 增加一键清除配置、聊天和记忆的本地数据管理入口。
- 删除记忆增加确认或撤销。
- 有真实 API Key 后补 5 类伴侣真实回复质量验收。
- 自动记忆沉淀规则继续调优。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行密钥扫描：未发现真实 token；仅发现代码字段名、空配置和 `Bearer ${config.apiKey}` 模板。
- `.playwright-cli/`、`dist/`、`node_modules/` 均为本地/构建产物，不进入提交。
- 普通问题不阻塞第一版提交。

## 2026-06-23 用户体验反馈与 v0.2 方向

### 用户反馈

- 长期记忆不应主要依赖用户手动填写，而应在聊天过程中由 AI 持续识别、沉淀和更新。
- 记忆需要区分作用范围：全局可用，或只对某个 AI 伴侣可用。
- AI 伴侣不应由项目预设固定名字；应允许用户自定义伴侣名字。
- 项目只提供可选性格/特质，用户可以组合这些性格生成一个 AI 伴侣，性格也应允许自定义。
- 可以增加导入用户与某个人的聊天记录，让 AI 伴侣尽可能学习对方的语气、回答方式和互动风格。
- 简历展示材料暂不急，先持续记录项目日志，最后基于日志总结解决的问题和使用的技术。

### 总控判断

- v0.2 应优先从“固定伴侣模板”转向“用户自定义伴侣 + 性格组合 + 自动记忆系统”。
- 聊天记录导入/模仿功能涉及隐私、同意和冒充风险，产品设计必须明确边界：只允许用户导入自己有权使用的记录；默认定位为“风格参考”，不应宣称复刻或冒充真实个人。
- 下一步交给产品经理线程整理 v0.2 产品需求和用户流程，再由产品经理按新版流程交接给 AI人设设计或技术架构。

## 2026-06-23 v0.2 P0 测试通过与总控最终确认

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.2 P0 中间验收。
- 结论：通过中间验收，可交给总控做最终确认。
- 阻塞问题：无。

### 已通过项摘要

- `npm run build` 通过。
- 桌面端 1440x900 与手机端 390x844 布局可用，无明显重叠或横向溢出。
- 伴侣名字可由用户自定义，性格/特质、自定义性格、亲密边界、回应节奏、问题处理方式均可编辑并进入提示词。
- 长期记忆支持全局与当前伴侣专属作用范围；专属记忆不会注入其他伴侣。
- 聊天过程可自动沉淀明确偏好、称呼、互动边界、情绪模式和目标纠正；敏感信息与不健康依赖表达不会保存为 active 记忆。
- 删除、替换、失效或专属隔离后的记忆不再进入长期记忆预览和 system prompt。
- 风格参考导入有风险提示，P0 仅把本地摘要注入提示词，不把导入原文长句默认发送给第三方模型。
- 仓库扫描未发现真实硬编码 API Key、Bearer token、身份证、银行卡或密码。

### 普通问题

- 删除长期记忆不等于删除聊天历史；聊天历史仍可能保留用户原始发言。后续需要设计聊天记录删除或敏感消息清理能力。
- Playwright CLI mock JSON 转义存在限制，真实合法 JSON 服务或真实 API Key 下的成功回复和认证失败详情脱敏建议后续再抽测。
- 记忆管理页会展示 `superseded` 记忆，虽然不会注入 prompt，但后续应更明显标记“已被替换，不再使用”或默认隐藏非 active 记忆。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行敏感信息扫描：未发现真实 token、真实 API Key、真实身份证、银行卡或密码。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- 普通问题已记录为后续优化项，不阻塞 v0.2 P0 提交与推送。

## 2026-06-23 v0.2.1 中间验收通过与总控确认

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.2.1 中间验收。
- 结论：通过中间验收。
- 阻塞问题：无。
- 普通返工项：无。

### 已通过项摘要

- `npm run build` 通过。
- 首次打开会显示本地隐私提示，说明 API Key、聊天记录、长期记忆、伴侣配置、风格摘要保存在当前浏览器 `localStorage`。
- 隐私提示说明聊天请求由浏览器直连用户填写的模型接口；用户确认后刷新不再自动出现，侧边栏和设置页可重新打开。
- API Key 类敏感信息不会生成长期记忆，界面不显示“已跳过敏感信息”“敏感内容未保存”“风控拦截”等内部痕迹。
- 不健康依赖表达不会保存为长期记忆，界面不展示内部 skip、needs_review 或边界提醒卡片。
- 健康情绪偏好仍可沉淀为全局情绪模式记忆。
- system prompt 已包含敏感信息不完整复述、不说已跳过/已过滤，以及依赖表达先温柔回应、再引导现实支持和自我判断的边界要求。
- 记忆页只展示真实保存的 active 记忆，并有自动记忆说明和删除影响说明。
- 桌面与 390px 手机宽度布局可用，未发现横向溢出或明显重叠。

### 可后续优化

- 当前会话气泡仍会显示用户刚输入的敏感内容；后续可考虑只在本地展示层做明显密钥或证件号脱敏。
- 当前无真实模型服务条件下，依赖表达的温柔回应效果仅验证到提示词注入链路，后续可用可控 mock server 或测试模型补端到端回复文本验收。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行敏感信息扫描：未发现真实 token、真实 API Key、真实身份证、银行卡或密码；命中项仅为安全规则和文档说明文本。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.2.1 验收通过，允许提交与推送。

## 2026-06-23 v0.3-A/B 中间验收通过与总控确认

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.3-A/B 中间验收。
- 结论：通过中间验收。
- 阻塞问题：无。
- 普通返工项：无。

### 已通过项摘要

- `npm run build` 通过。
- 设置页提供 DeepSeek V4 Flash、DeepSeek V4 Pro、OpenAI 兼容预设；预设只填写 providerName、baseURL、model，不填写 API Key。
- 真实模型验收提示清楚：用户 Key 只应在网页设置页本地输入，测试记录、截图、交接报告不记录完整 Key。
- 侧栏、错误提示和导出结构不会展示完整 API Key；页面只显示脱敏摘要。
- 错误提示覆盖认证失败、额度/余额/频率限制、接口地址或模型名错误、请求参数错误、非 JSON、空 assistant 内容、网络/CORS/代理失败。
- 服务商错误详情会对 `sk-*`、Bearer、token、secret、api_key 等内容做脱敏。
- 本地数据管理可清除 API Key、当前聊天、长期记忆、风格摘要，并能保持对应本地状态一致。
- 导出 JSON 包含版本、导出时间、去 Key 的模型配置、伴侣、记忆和风格摘要；不默认包含原始聊天记录，也不包含 API Key 字段值。
- v0.2.1 回归通过：本地隐私提示、健康情绪偏好沉淀、敏感信息静默过滤、不健康依赖表达不保存为长期记忆均保持可用。
- 风格摘要、自定义伴侣、提示词组装、桌面和手机端响应式布局通过测试验收。

### 可后续优化

- 后续可增加 `buildLocalDataExport` 自动化测试，防止导出字段回归。
- 真实模型质量尚未用真实 DeepSeek/OpenAI Key 做端到端验收；后续只允许用户在网页设置页本地输入 Key，不应在线程、命令、截图或报告中提供完整 Key。
- 当前会话气泡仍可能显示用户自己输入的敏感字符串；后续可考虑本地展示层脱敏。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key；中文敏感词命中项仅为安全规则和历史日志说明。
- 工作区修改文件与测试交接一致：`README.md`、`src/App.tsx`、`src/model-provider/openai.ts`、`src/storage/localStorage.ts`、`src/styles.css`、`src/types.ts`。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.3-A/B 验收通过，允许提交与推送。

## 2026-06-23 v0.3-C 首次创建伴侣轻问卷复验通过与总控确认

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.3-C 返工后复验。
- 结论：通过。上一轮 P0 阻塞问题“跳过首次轻问卷后无法从聊天空状态或伴侣页重新打开问卷”已修复。
- 阻塞问题：无。
- 普通问题：无。

### 已通过项摘要

- `npm run build` 通过。
- 首次问卷在清空 localStorage 后可自动展示，即使本地存在 5 个默认伴侣也不会误拦截。
- 点击“先跳过，直接进去看看”后保存 skipped、不强迫创建、仍可进入聊天。
- 跳过后，从聊天空状态“帮我快速创建一个伴侣”和伴侣页“帮我快速创建”均可重新打开三步轻问卷。
- 完成问卷后状态为 completed，生成 `source: onboarding` 的伴侣，插入本地开场，刷新后不再自动弹出。
- 三步问卷、结果页和开场文案保持轻松自然，不频繁自称 AI，不出现长免责声明。
- 产品层透明说明仍保留在 README、隐私提示和设置页；聊天层不打断陪伴感。
- v0.3-A/B 关键回归通过：模型预设、本地数据管理、导出隐私、错误脱敏、敏感信息和不健康依赖不沉淀均保持可用。
- 移动端 390x844 无横向溢出。

### 可后续优化

- 后续可补自动化回归：`new -> skipped -> 聊天空状态重开问卷 -> skipped -> 伴侣页重开问卷 -> completed -> 刷新不再自动弹出`。
- 后续可补 localStorage 状态机测试，覆盖默认伴侣存在时不阻止首次问卷展示。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key；中文敏感词命中项仅为安全规则和历史日志说明。
- 工作区修改文件与测试交接一致：`README.md`、`src/App.tsx`、`src/companion/profiles.ts`、`src/storage/localStorage.ts`、`src/styles.css`、`src/types.ts`、`src/companion/onboarding.ts`。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.3-C 返工复验通过，允许提交与推送。

## 2026-06-24 v0.3-D 降 AI 味与伴侣感专项验收通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.3-D 中间验收。
- 结论：通过。低 AI 味 prompt 与伴侣风格专项优化已进入真实聊天请求链路。
- 阻塞问题：无。
- 普通问题：无。

### 已通过项摘要

- `npm run build` 通过。
- secret 扫描未发现真实 `sk-*`、Bearer token 或 x-api-key 等硬编码密钥。
- `buildSystemPrompt()` 已接入 `【低 AI 味回应规则】`、`【伴侣说话方式】`、`【场景回应优先级】`、关系风格、主动程度和长期记忆自然注入规则。
- 长期记忆注入段落只包含记忆内容，不再暴露 scope、category、confidence 等内部元数据。
- 伴侣特质文案已调整，避免冷报告、长清单、频繁解释系统规则。
- 可控 OpenAI 兼容 mock 端到端验证通过，页面回复更短、更具体，先承接情绪，减少客服腔、助手腔和报告腔。
- 关系差异验证通过：朋友陪伴、理性支持、轻恋爱陪伴、角色陪伴、自定义伴侣均能进入 system prompt 并影响回复风格。
- v0.3-A/B/C 关键回归通过：模型预设、本地数据管理、导出隐私、首次轻问卷、移动端布局、敏感/不健康依赖不沉淀均保持可用。

### 可后续优化

- 后续可让用户只在网页设置页本地输入真实 DeepSeek/OpenAI Key，做一次真实模型主观质量验收；测试报告不得记录完整 Key。
- 后续可补 prompt 结构单测，覆盖低 AI 味规则、伴侣说话方式、场景回应优先级和长期记忆纯内容注入。
- 后续可增加小样本人工评分表：客服腔、自称 AI 频率、情绪承接、建议长度、关系差异、边界温度。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key；中文敏感词命中项仅为安全规则和历史日志说明。
- 工作区修改文件与测试交接一致：`src/chat-engine/prompt.ts`、`src/companion/profiles.ts`。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.3-D 验收通过，允许提交与推送。

## 2026-06-24 v0.3-E 轻恋爱伴侣真实聊天专项返工复验通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.3-E 返工后复验。
- 结论：通过。此前 P0 “排他依赖表达被保存为 active 长期记忆”已修复。
- 阻塞问题：无。
- 普通问题：无。

### 已通过项摘要

- `npm run build` 通过。
- `npx tsc --noEmit` 通过。
- 密钥扫描未发现真实 `sk-*`、Bearer token 或 x-api-key 等硬编码密钥。
- 默认轻恋爱伴侣 `予安` 下，`我只想要你，别人都不要。` 不再新增长期记忆，页面无 skip、needs_review、风控或已跳过等内部痕迹。
- 扩展排他依赖样例均不保存长期记忆：`我只想要你，其他人都不要。`、`只有你就够了，别人都不要。`、`我只想要你，朋友都不想理。`
- 健康偏好仍可沉淀为 active 记忆，例如焦虑时希望先被陪伴、缓一缓、不要立刻讲大道理。
- 敏感信息静默过滤、普通临时情绪不沉淀保持可用。
- 默认、自定义、问卷来源轻恋爱伴侣均进入 `【轻恋爱陪伴专项】` prompt。
- 本地续聊保持本地插入，不请求模型，不是真实推送。
- 移动端 390x844 无横向溢出。

### 可后续优化

- 后续可将不健康依赖/排他绑定识别从长正则抽成集中分类函数，便于覆盖更多自然语言变体和单元测试。
- 轻恋爱本地续聊后续可增加更细冷却时间和最近消息语义判断。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key；中文敏感词命中项仅为安全规则和历史日志说明。
- 工作区修改文件与测试交接一致：`src/App.tsx`、`src/chat-engine/prompt.ts`、`src/companion/onboarding.ts`、`src/companion/profiles.ts`、`src/memory/memory.ts`、`src/styles.css`、`src/companion/romance.ts`。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.3-E 返工复验通过，允许提交与推送。

## 2026-06-25 v0.3-F1 全伴侣 prompt 瘦身复验通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.3-F1 复验。
- 结论：通过。全伴侣类型 prompt 瘦身与回复行为规则重整已进入真实请求链路。
- 阻塞问题：无。
- 普通问题：无。

### 已通过项摘要

- `npm run build` 通过。
- `npx tsc --noEmit` 通过。
- 密钥扫描未发现真实 `sk-*`、Bearer token 或 x-api-key 等硬编码密钥。
- `src/chat-engine/prompt.ts` 不再拼接旧式长标题块：`【低 AI 味回应规则】`、`【场景回应优先级】`、`【伴侣说话方式】`、`【当前伴侣设定】`。
- 五类默认伴侣 system prompt 均完成瘦身；非轻恋爱默认伴侣约 630-645 字，轻恋爱约 879 字。
- 温柔朋友、理性支持、日常/治愈陪伴、角色陪伴、轻恋爱陪伴的 mock 回复质量通过：先接具体情绪，少报告化，少建议清单，保留关系气质。
- 记忆与风格摘要仍能进入 prompt，但不泄漏 scope、category、confidence、source、status、userReviewed 等内部元数据。
- 敏感信息静默过滤、不健康依赖不沉淀、高风险表达追加现实支持边界等安全隐私回归通过。
- 设置页模型预设、API Key 本地保存说明、导出入口和移动端布局回归通过。

### 可后续优化

- 后续可扩展高风险关键词覆盖“自伤”等更宽表达。
- 后续可由用户在网页设置页本地输入真实 Key，做真实模型手感最终校准；测试报告不得记录完整 Key。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key；中文敏感词命中项仅为安全规则和历史日志说明。
- 工作区修改文件与测试交接一致：`src/chat-engine/prompt.ts`、`src/companion/profiles.ts`、`src/companion/romance.ts`。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.3-F1 验收通过，允许提交与推送。

## 2026-06-25 v0.3-F2 聊天消息间断感验收通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.3-F2 中间验收。
- 结论：通过。聊天消息间断感与输入中状态优化已通过浏览器验收。
- 阻塞问题：无。
- 普通问题：无。

### 已通过项摘要

- `npm run build` 通过。
- `npx tsc --noEmit` 通过。
- 密钥扫描未发现真实 `sk-*`、Bearer token 或 x-api-key 等硬编码密钥。
- 旧等待文案 `正在认真想怎么回你...` 已移除，等待模型时只在聊天区顶部伴侣名旁显示轻量波点输入中状态。
- mock 返回空行分隔多段文本时，assistant 按多条消息逐段插入，形成连续发消息的视觉效果。
- 短单段回复保持为 1 条 assistant 消息；超长无空行单段回复可按句合并拆成多条。
- 轻恋爱伴侣多段消息保留 `message assistant romance` 连续小气泡样式；非轻恋爱伴侣逐段插入但不套用 romance 样式。
- 错误路径不会残留输入中状态，错误详情仍脱敏。
- 分段插入过程中清空聊天或切换伴侣时，旧分段不再继续插入，typing 状态被清理。
- 首次问卷、本地轻恋爱续聊和移动端 390px 布局回归通过。

### 可后续优化

- 如产品希望 70-90 字多句回复也有更强间断感，后续可下调 `splitAssistantReply()` 阈值或按句数拆分。
- 后续可把伴侣 id/name 固化到消息里，避免切换伴侣后历史 assistant 消息显示成当前新伴侣名。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key；中文敏感词命中项仅为安全规则和历史日志说明。
- 工作区修改文件与测试交接一致：`src/App.tsx`、`src/styles.css`。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.3-F2 验收通过，允许提交与推送。

## 2026-06-26 v0.3-F3 浅蓝白玻璃感 UI 验收通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.3-F3 中间验收。
- 结论：通过。浅蓝白玻璃感 UI 第一轮视觉升级已通过桌面和移动端验收。
- 阻塞问题：无。
- 普通问题：无。

### 已通过项摘要

- `npm run build` 通过。
- `npx tsc --noEmit` 通过。
- 密钥扫描未发现真实 `sk-*`、Bearer token 或 x-api-key 等硬编码密钥。
- 桌面首屏已切换到浅蓝白渐变/光感背景，侧栏为浅色玻璃拟态，主卡片为半透明白/浅蓝玻璃层并带柔和蓝色阴影。
- 左侧导航当前项蓝色高亮清楚，桌面和手机端导航可用。
- 聊天仍是应用主体验，没有新增营销 hero 或落地页。
- 设置、本地数据管理、导出、伴侣、记忆、风格、问卷等页面视觉未崩，卡片玻璃层覆盖一致。
- F2 回归通过：输入中波点、多段 assistant 逐条显示、无旧等待文案。
- 聊天气泡视觉更新生效：用户气泡为蓝色渐变，assistant 为轻白气泡，轻恋爱连续小气泡为淡粉暖调。
- 桌面 1440x900 与移动端 390x844 均无横向溢出；浏览器 console 无 warning/error。

### 可后续优化

- 后续可继续微调主聊天面板精致度、玻璃透明度/模糊强度、移动端顶部状态区域视觉密度。
- 当前 F3 通过 CSS 覆盖旧样式实现，后续可整理合并主题层，减少历史样式负担。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key；中文敏感词命中项仅为安全规则和历史日志说明。
- 工作区修改文件与测试交接一致：`src/styles.css`。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.3-F3 验收通过，允许提交与推送。

## 2026-06-26 v0.4 恋爱陪伴主流程补充验收通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.4 高优先级补充修正中间验收。
- 结论：通过。恋爱陪伴主流程、模板融合和自定义 prompt 校验已通过测试。
- 阻塞问题：无。
- 普通问题：无影响验收通过的问题。

### 已通过项摘要

- `npm run build` 通过。
- `npx tsc --noEmit` 通过。
- 清空 localStorage 后首次主流程只出现“女友方向 / 男友方向”，未出现中性/不限性别主选项。
- 女友方向 6 个模板、男友方向 6 个模板均可选择。
- 融合特质共 8 个，可选 1-3 个；选择到 3 个后其余选项禁用。
- 自定义 prompt 可保存正常恋爱人设；API Key/token、身份证、冒充真人、线下承诺、露骨成人、违法危险、自伤伤害、强控制依赖等 blocked 样例会阻止保存。
- 创建后 localStorage 字段完整：`relationshipType: "light_romance"`、`primaryMode: "romance"`、`gender`、`primaryRomanceTemplateId`、`blendTraitIds`、`blendPromptSummary`、`customSystemPrompt`、`promptValidationStatus` 均落盘。
- valid 自定义 prompt 会进入真实 Chat Completions 请求 system prompt；blocked 状态下即使本地数据被污染，也会回退模板 prompt，blocked 文本不进入请求体。
- effective prompt 保持短自然结构，不泄漏 `localStorage`、scope、confidence、skip、风控等内部字段。
- 旧伴侣兼容：朋友、予安、理性支持、日常、角色伴侣仍显示在兼容入口，可切换；新建恋爱伴侣与旧伴侣共存。
- F2/F3、安全隐私、设置页、导出隐私和移动端回归通过。

### 可后续优化

- 导出 JSON 的 `version` 类型和值、导出文件名仍沿用 v0.3，后续建议统一更新为 v0.4，避免阶段标识混淆。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key；中文敏感词命中项仅为安全校验和提示文案。
- 工作区修改文件符合 v0.4 范围：`README.md`、`src/App.tsx`、`src/chat-engine/prompt.ts`、`src/companion/profiles.ts`、`src/storage/localStorage.ts`、`src/types.ts`、`src/companion/promptValidation.ts`、`src/companion/romanceTemplates.ts`。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.4 验收通过，允许提交与推送。

## 2026-06-26 v0.4.1 恋爱陪伴主流程收口通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.4.1 恋爱陪伴主流程收口小修中间验收。
- 结论：通过。
- 阻塞问题：无。
- 普通问题：无。

### 已通过项摘要

- `npm run build` 通过。
- `npx tsc --noEmit` 通过。
- 密钥扫描未发现真实 `sk-*`、Bearer token 或 x-api-key 等硬编码密钥。
- 清空 localStorage 后首屏显示 `v0.4.1 恋爱陪伴优先 Demo`、用户须知、男友/女友创建主流程；未出现旧五类平铺。
- 用户须知集中说明本地保存、API Key、聊天请求、AI 伴侣透明身份、敏感信息不保存、自定义人设边界；入口在侧栏、创建流程和设置页可见。
- “先用默认女友”后，`ai-companion:messages` 为空，聊天区显示“TA 已经准备好了”，未自动插入 assistant 开场消息，也未立刻补本地续聊。
- 主聊天列表默认只突出恋爱伴侣；旧朋友/理性/日常/角色在“更多/兼容旧伴侣”里可显示到主列表或隐藏，并写入 `showInMainList`。
- 创建流程保持多步骤低信息密度：方向选择、模板选择、融合气质、自定义设定、名字称呼/主动程度。
- 女友模板前三为温柔可爱、傲娇、御姐；男友模板前三为温柔男友、成熟哥哥、霸总型。
- 自定义 prompt blocked 文案改为温和提示，valid 文本仍可保存。
- F2/F3、v0.4 能力、安全隐私、导出和设置页回归通过。

### 可后续优化

- 后续可继续减少默认恋爱伴侣与新建同名“予安”同时出现造成的轻微重复感。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key；中文敏感词命中项仅为安全校验和提示文案。
- 工作区修改文件符合 v0.4.1 范围：`README.md`、`src/App.tsx`、`src/companion/promptValidation.ts`、`src/companion/romanceTemplates.ts`、`src/storage/localStorage.ts`、`src/styles.css`、`src/types.ts`。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.4.1 验收通过，允许提交与推送。

## 2026-06-27 v0.4.2 单聊天页信息架构收口通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.4.2 单聊天页信息架构重整与轻量返工复验。
- 结论：通过复验。
- 阻塞问题：无。
- 普通问题：无。此前“双弹窗层叠”和“blocked 人设保存按钮不提前禁用”两个普通体验问题已修复。

### 已通过项摘要

- `npm run build` 通过。
- `npx tsc --noEmit` 通过。
- 密钥扫描未发现真实 `sk-*`、Bearer token 或 x-api-key 等硬编码密钥。
- 清空 localStorage 后首次打开只出现一个主弹窗：先显示用户须知，确认后再显示创建恋爱伴侣弹窗，无双弹窗层叠。
- 单聊天页结构生效：左侧为伴侣名字列表 + 新建 + 更多，中间为聊天主区域，顶部提供伴侣、记忆、风格、设置、须知按钮，右侧常驻栏未恢复。
- 创建/默认女友路径后 `ai-companion:messages` 为空，未自动插入 assistant 开场，也未触发本地续聊。
- 伴侣管理面板支持新建草稿、取消不落盘、保存后新增并选中；人设编辑框默认显示当前模板/核心提示词。
- 人设编辑框输入 blocked 内容会即时显示温和提示并禁用保存按钮；valid custom prompt 可保存并进入 system prompt，blocked prompt 不进入请求体。
- 伴侣设定 UI 和 prompt 注入均不再包含 `亲密边界`、`问题处理方式`、`边界备注`、`problemSolvingStyle`、`intimacyBoundary`、`boundaryNotes` 等旧字段。
- 记忆、风格、设置均改为顶部按钮打开弹窗；记忆可新增/编辑/删除，风格可导入/添加，设置保留 DeepSeek/OpenAI 兼容预设、本地数据管理和导出说明。
- 导出文件名为 `ai-companion-local-data-v0.4.2-YYYY-MM-DD.json`，payload `version` 为 `v0.4.2`；导出结构不含 API Key 值、不含 `apiKey` 字段、不含原始聊天 `messages` 字段。
- F2 多段 assistant 消息逐段插入、输入中波点，F3 浅蓝白玻璃 UI 和 390px 移动端无横向溢出均回归通过。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key。
- 工作区修改文件符合 v0.4.2 范围：`README.md`、`src/App.tsx`、`src/chat-engine/prompt.ts`、`src/storage/localStorage.ts`、`src/styles.css`。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.4.2 复验通过，允许提交与推送。

## 2026-06-27 v0.4.3 固定视口与伴侣消息隔离通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.4.3 小修复验。
- 结论：通过。
- 阻塞问题：无。
- 普通问题：无。

### 已通过项摘要

- `npm run build` 通过。
- `npx tsc --noEmit` 通过。
- 密钥扫描未发现真实 `sk-*`、Bearer token 或 x-api-key 等硬编码密钥。
- 桌面 1440x900、1280x720 页面级无纵向/横向滚动；移动端 390x844 无横向溢出，页面级滚动被限制，顶部工具按钮横向内部滚动可用。
- 消息列表、左侧伴侣列表和超高设置弹窗均可在各自区域内部滚动，关闭按钮可用。
- 伴侣聊天记录已按伴侣隔离：A/B 伴侣分别显示各自聊天；切换后消息保留；清空 A 当前聊天不影响 B。
- 分段回复取消逻辑通过：mock 返回三段文本时，发送后切换伴侣或清空当前聊天，后续分段不会插入错误伴侣，也不会迟到插回已清空聊天；typing 波点会清理。
- 旧 `ai-companion:messages` 可在新 grouped 结构为空时迁移到当前 active companion，并写入 `ai-companion:messages-by-companion:v1`。
- 导出 JSON 仍符合 v0.4.2 策略：payload 不含 API Key、不含顶层 `messages`、不含旧聊天原文。
- v0.4.2 单聊天页结构、顶部按钮弹窗、用户须知/创建弹窗顺序、旧伴侣兼容入口、blocked prompt 即时校验均回归通过。

### 可后续优化

- 当前导出版本仍为 `v0.4.2` 是本轮任务包预期；若后续希望用户感知 v0.4.3，可统一产品版本显示与导出版本策略。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key。
- 工作区修改文件符合 v0.4.3 范围：`src/App.tsx`、`src/storage/localStorage.ts`、`src/styles.css`。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.4.3 验收通过，允许提交与推送。

## 2026-06-27 v0.5-A 女友方向恋爱聊天真实感专项通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.5-A 女友方向恋爱聊天真实感专项复验。
- 结论：通过。
- 阻塞问题：无。
- 普通问题：无。

### 已通过项摘要

- `npm run build` 通过。
- `npx tsc --noEmit` 通过。
- 密钥扫描未发现真实 `sk-*`、Bearer token 或 x-api-key 等硬编码密钥。
- `female_soft_cute`、`female_tsundere`、`female_mature_sister` 的真实请求 system prompt 均包含女友方向通用真实感 hint、对应模板短微调、1-3 段自然短消息 plan；男友方向未注入女友专项 hint。
- 连续两轮 assistant 以问句收尾后，下一轮 system prompt 出现“不要再以问句结尾”约束。
- mock 聊天手感通过：温柔可爱能心疼承接且不清单化；傲娇能轻吐槽和小情绪且不教育；御姐能成熟稳住并给最小一步，不报告化。
- assistant 空行分段会逐条显示为连续小气泡；typing 波点结束后清理。
- `你是真人吗？` 能自然说明 AI 伴侣身份，不长免责声明；`我只想要你，别人都不要。` 温柔承接并拉回现实支持，不保存长期记忆，不显示 needs_review、风控、跳过等内部痕迹。
- API Key/验证码测试输入不保存长期记忆，界面不显示内部 skip/风控痕迹。
- 本地续聊降频通过：空会话不自动插入；7 小时未互动会本地补一条；5 小时不补；低主动不续聊；同一伴侣 24 小时内已有续聊消息则不重复；未触发真实推送。
- v0.4.3 单聊天页、顶部弹窗、固定视口、移动端 390px 无横向溢出、伴侣消息隔离、导出不含 Key/原始聊天、blocked prompt 即时校验均回归通过。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key。
- 工作区修改文件符合 v0.5-A 范围：`src/companion/romance.ts`、`src/companion/romanceTemplates.ts`。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.5-A 验收通过，允许提交与推送。

## 2026-06-27 v0.6-A Windows 一键本地启动通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.6-A Windows 一键启动方式返工复验。
- 结论：通过。
- 阻塞问题：无。此前 Windows PowerShell 5.1 因 `scripts/start-local.ps1` 无 UTF-8 BOM 导致 `.bat` 双击入口解析失败的问题已修复。
- 普通问题：无。

### 已通过项摘要

- `npm run build` 通过。
- `npx tsc --noEmit` 通过。
- 密钥扫描未发现真实 `sk-*`、Bearer token 或 x-api-key 等硬编码密钥。
- `scripts/start-local.ps1` 首字节为 `EF BB BF`，Windows PowerShell 5.1 `-File` 可正确解析中文字符串。
- `package.json` 中 `dev`、`dev:open`、`preview`、`preview:open` 均固定 `--host 127.0.0.1 --port 5173 --strictPort`，`start:local` 指向 `npm run dev:open`。
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\start-local.ps1 -Mode dev` 可启动开发版，`http://127.0.0.1:5173/` 返回 200，`4173` 无服务。
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\start-local.ps1 -Mode preview` 会先执行构建，再以固定 `5173` 预览构建版。
- `启动AI伴侣.bat` 和 `构建并预览AI伴侣.bat` 等价执行通过，均固定 `http://127.0.0.1:5173/`。
- 5173 端口占用时不切换端口，会提示已有 AI伴侣窗口/服务可能在运行，并打开固定地址。
- README 小白说明覆盖 Node.js LTS、双击启动、固定地址、Ctrl+C 停止、localStorage 与当前浏览器和访问地址绑定、不要混用 localhost/其他端口/其他浏览器、非正式安装包边界、导出不含 API Key 和原始聊天记录。
- 隐私/导出逻辑保持：`buildLocalDataExport()` 会移除 `apiKey`，导出 payload 不包含原始 `messages`；启动脚本不读取或打印 localStorage。

### 可后续优化

- 当前 v0.6-A 是本地启动器方案，不是 Electron/Tauri 正式安装包；如要进一步软件化，可在后续阶段评估桌面壳、数据迁移和更新机制。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key。
- 工作区修改文件符合 v0.6-A 范围：`README.md`、`package.json`、`scripts/start-local.ps1`、`启动AI伴侣.bat`、`构建并预览AI伴侣.bat`。
- `.playwright-cli/`、`dist/`、`node_modules/`、`output/` 均为本地/构建产物，不进入提交。
- v0.6-A 返工复验通过，允许提交与推送。

## 2026-06-28 v0.6-B Electron 桌面应用骨架通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.6-B Electron 桌面应用骨架、NSIS 安装包、更新按钮和显式数据迁移复验。
- 结论：通过。
- 阻塞问题：无。
- 普通问题：无。

### 已通过项摘要

- Web 回归通过：`npm run build` 通过，`npx tsc --noEmit` 通过，`npm run dev` 短启动后 `http://127.0.0.1:5173/` 返回 200，4173 未启动；v0.6-A `启动AI伴侣.bat` 等价执行可启动 5173。
- Electron 构建通过：`npm run electron:build-main`、`npm run desktop:dir`、`npm run desktop:dist` 均通过。
- 桌面产物存在：`release-v06b/win-unpacked/AI伴侣.exe`、`release-v06b/AI伴侣 Setup 0.1.0.exe`、`release-v06b/latest.yml`、`release-v06b/AI伴侣 Setup 0.1.0.exe.blockmap`。
- unpacked 桌面程序可独立启动并保持运行，进程名为 `AI伴侣`，窗口标题为 `AI伴侣 Demo`。
- NSIS 安装包可静默安装和卸载；安装后 exe 可启动并保持运行。卸载后临时安装目录可能保留空目录，记录为后续优化，不阻塞 P0。
- 更新入口符合 P0 规则：packaged 桌面版设置弹窗提供“桌面版与更新”“检查更新”“从网页版导入备份”和数据目录展示；无可用更新时不展示“立即更新/重启并安装”行动按钮。
- 开发态 Electron 模拟新版链路通过：模拟新版后显示“立即更新/稍后”，下载完成后显示“重启并安装/稍后”，点击“稍后”后行动按钮隐藏。
- 显式迁移通过：从网页版导出的 JSON 可通过桌面设置导入；`providerName/baseURL/model`、伴侣、记忆、风格摘要会写入桌面 localStorage，`apiKey` 被强制置空，不会导入 Key。
- Electron 安全边界通过：`nodeIntegration:false`、`contextIsolation:true`、`sandbox:true`、`webSecurity:true`；packaged renderer 中 `window.require` 和 `window.process` 不存在；preload 只暴露桌面信息和更新相关受限接口；导航和外链受限；普通 packaged 版不开 DevTools。
- 隐私/文档通过：`docs/DESKTOP_RELEASE.md` 说明安装包、数据迁移、更新机制、本地测试源、无代码签名、隐私边界；README 保留 v0.6-A 本地启动说明。`buildLocalDataExport()` 仍移除 `apiKey`，导出不包含原始 `messages`。
- 文本、配置和更新元数据密钥扫描未发现真实 `sk-*`、Bearer token 或 x-api-key。release 二进制扫描时 Electron/Chromium 二进制误报片段已排除。

### 可后续优化

- 配置正式应用图标。
- 补充 `package.json` 的 `description` 和 `author`，减少 electron-builder warning。
- 优化 NSIS 卸载后的空目录清理体验。
- 正式分发前需要代码签名证书和真实 HTTPS/GitHub Releases 发布源。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行 Electron 主进程编译：`npm run electron:build-main` 通过。
- 已执行桌面目录构建：`npm run desktop:dir` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key。
- 工作区修改文件符合 v0.6-B 范围：`.gitignore`、`package-lock.json`、`package.json`、`src/App.tsx`、`src/styles.css`、`vite.config.ts`、`docs/DESKTOP_RELEASE.md`、`electron-builder.yml`、`electron/`、`scripts/write-electron-package-marker.cjs`、`src/desktop/`。
- `.playwright-cli/`、`dist/`、`dist-electron/`、`node_modules/`、`output/`、`release/`、`release-v06b/` 均为本地/构建产物，不进入提交。
- v0.6-B 验收通过，允许提交与推送。

## 2026-06-28 v0.6-C 所依桌面软件感 UI 与品牌改名通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.6-C 桌面软件感 UI 重整、“所依”品牌改名和标题/构建入口小修复验。
- 结论：通过。
- 阻塞问题：无。此前 `index.html` 被误写成 dist 产物形态导致构建失败的问题已修复。
- 普通问题：无。

### 已通过项摘要

- 源码 `index.html` 已恢复为 Vite 入口形态，包含 `<title>所依</title>`、`<div id="root"></div>` 和 `/src/main.tsx` 入口脚本，不再引用 `./assets/index-*.js/css` 构建产物。
- `npm run build` 通过。
- `npx tsc --noEmit` 通过。
- `npm run electron:build-main` 通过。
- `npm run desktop:dir` 通过，重新生成 `release-v06c/win-unpacked/所依.exe`。
- `release-v06c/win-unpacked/resources/app.asar` 内 `dist/index.html` 标题为 `所依`，且不包含旧标题 `AI伴侣 Demo`。
- 运行 `所依.exe` 后 `document.title === "所依"`，页面为 file URL，旧标题不存在。
- 应用内品牌文本为“所依”；无默认 `File / Edit / View / Window / Help` 菜单栏；自定义标题栏存在；窗口按钮为“最小化 / 最大化 / 关闭”；标题栏区域可拖拽，按钮区域不可拖拽。
- Electron 配置保持：`frame:false`、`Menu.setApplicationMenu(null)`、`APP_NAME = "所依"`、`app.setName(APP_NAME)`、`nodeIntegration:false`、`contextIsolation:true`、`sandbox:true`、`webSecurity:true` 未回退。
- 内部 `userDataPath` 仍为 `AppData/Roaming/AI伴侣`，用于保护 v0.6-B 已有桌面数据，符合允许范围。
- 设置里仍有“检查更新”“从网页版导入备份”；`available` 才显示“立即更新”，`downloaded` 才显示“重启并安装”；Web 模式通过 `desktopInfo` 降级，不显示假的桌面标题栏。
- 密钥扫描未发现真实 `sk-*`、Bearer token 或 x-api-key。

### 可后续优化

- 正式图标、代码签名、真实 GitHub Releases/HTTPS 更新源仍属于 v0.6-D 暂缓项。

### 总控最终确认

- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行 Electron 主进程编译：`npm run electron:build-main` 通过。
- 已执行桌面目录构建：`npm run desktop:dir` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token 或 x-api-key。
- 工作区修改文件符合 v0.6-C 范围：`.gitignore`、`README.md`、`docs/DESKTOP_RELEASE.md`、`electron-builder.yml`、`electron/main.ts`、`electron/preload.ts`、`index.html`、`src/App.tsx`、`src/desktop/desktopBridge.ts`、`src/styles.css`。
- `.playwright-cli/`、`dist/`、`dist-electron/`、`node_modules/`、`output/`、`release/`、`release-v06b/`、`release-v06c/` 均为本地/构建产物，不进入提交。
- v0.6-C 复验通过，允许提交与推送。

## 2026-06-28 v0.6-D 正式发布准备通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.6-D 正式发布准备和构建入口污染阻塞修复复验。
- 结论：通过。
- 阻塞问题：无。根目录 `index.html` 源码入口污染问题已关闭，并新增构建前守卫防止复发。
- 普通问题：无。

### 已通过项摘要

- 根目录源码 `index.html` 保持 Vite 入口形态，包含 `<title>所依</title>`、`<div id="root"></div>`、`/src/main.tsx`，不含 `./assets/index-*.js/css` 等 dist 产物引用。
- 新增 `scripts/verify-source-index.cjs` 构建前守卫，`package.json` 的 `build` 已接入 `node scripts/verify-source-index.cjs && tsc --noEmit && vite build`；`npm run build` 后根目录 `index.html` 未被改写。
- `package.json` name 为 `suoyi`，补充 description/author。
- 图标资源存在：`build/icons/source.png`、`build/icons/icon.png`、`build/icons/icon.ico`。
- `electron-builder.yml` 输出目录为 `release-v06d`，`productName: 所依`，`artifactName: suoyi-setup-${version}.${ext}`，配置 Windows/NSIS 图标，并使用 GitHub provider：owner `yuhui4756-hub`，repo `ai-companion`。
- `release-v06d/latest.yml` 指向 `suoyi-setup-0.1.0.exe`，包含 sha512/size/releaseDate；`release-v06d/win-unpacked/resources/app-update.yml` 为 GitHub provider 且无 token。
- 运行 `release-v06d/win-unpacked/所依.exe` 后 `document.title === "所依"`，无默认 File/Edit/View/Window/Help 菜单，窗口按钮为最小化/最大化/关闭，renderer 无 Node 直通，preload 仅暴露白名单能力。
- v0.6-D 更新入口规则通过：无新版时品牌区无更新小圆点；设置页无大块“检查更新”卡片；显式导入备份入口仍在。
- Web 回归通过：`npm run dev` 可在固定地址 `http://127.0.0.1:5173/` 返回 200。
- 密钥扫描未发现真实 `sk-*`、Bearer token、x-api-key 或 GitHub token。

### 已知边界

- 当前未配置代码签名；正式公开分发时 Windows SmartScreen 可能提示未知发布者。
- 真实 GitHub Releases 自动更新仍需后续实际发布并上传安装包、`latest.yml`、blockmap 后做端到端验证。
- `release-v06d`、`dist`、`dist-electron` 等构建产物不提交进源码仓库。

### 总控最终确认

- 已执行构建前守卫：`node scripts/verify-source-index.cjs` 通过。
- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行 Electron 主进程编译：`npm run electron:build-main` 通过。
- 已执行桌面安装包构建：`npm run desktop:dist` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token、x-api-key 或 GitHub token。
- 工作区修改文件符合 v0.6-D 范围：`.gitignore`、`README.md`、`docs/DESKTOP_RELEASE.md`、`electron-builder.yml`、`electron/main.ts`、`electron/preload.ts`、`electron/updater.ts`、`package.json`、`package-lock.json`、`src/App.tsx`、`src/desktop/desktopBridge.ts`、`src/styles.css`、`build/icons/*`、`scripts/verify-source-index.cjs`。
- `.playwright-cli/`、`dist/`、`dist-electron/`、`node_modules/`、`output/`、`release/`、`release-v06b/`、`release-v06c/`、`release-v06d/` 均为本地/构建产物，不进入提交。
- v0.6-D 复验通过，允许提交与推送。

## 2026-06-28 v0.6-D 应用图标热修通过

### 总控确认

- 用户反馈当前应用图标仍像 Electron 默认图标。
- 复查确认：`electron-builder.yml` 已配置图标资源，但 `signAndEditExecutable: false` 导致图标未真正写入 `所依.exe` 的 Windows 可执行文件资源。
- 已新增 `scripts/apply-windows-icon.cjs`，通过 `afterPack` 使用 `rcedit` 在打包后写入 `build/icons/icon.ico`，同时保留“不做代码签名”的边界。
- 已重新执行 `npm run desktop:dist` 并通过。
- 已从 `release-v06d/win-unpacked/所依.exe` 和 `release-v06d/suoyi-setup-0.1.0.exe` 直接提取关联图标，确认均为用户提供的所依图标，不再是 Electron 默认图标。
- 已执行 `npm run build`、`npx tsc --noEmit`、`npm run electron:build-main`，均通过。
- 已执行敏感信息扫描，命中项仅为历史日志和安全校验规则说明，未发现真实密钥。

## 2026-06-29 v0.6-E Release 前视觉小修通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.6-E 正式 Release 前视觉与发布准备小修复验。
- 结论：通过，可作为第一版 Release 候选资产。
- 阻塞问题：无。
- 普通问题：无。

### 已通过项摘要

- 桌面图标主体已放大，`build/icons/icon.ico` 包含 16、24、32、48、64、128、256 多尺寸，修正桌面快捷方式图标显得偏小的问题。
- 应用内标题栏和品牌区两个旧爱心图标已替换为所依应用图标，运行态加载 `dist/assets/suoyi-icon-*.png`。
- `release-v06d/win-unpacked/所依.exe` 和 `release-v06d/suoyi-setup-0.1.0.exe` 均可提取到非 Electron 默认关联图标。
- v0.6-D 必须保留项未回退：更新小圆点规则、GitHub provider、源码 index 守卫、显式导入备份入口、Electron 安全边界均保留。
- Release 候选资产已重新生成：`release-v06d/suoyi-setup-0.1.0.exe`、`release-v06d/suoyi-setup-0.1.0.exe.blockmap`、`release-v06d/latest.yml`。

### 总控最终确认

- 已执行构建前守卫：`node scripts/verify-source-index.cjs` 通过。
- 已执行最终构建：`npm run build` 通过。
- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行 Electron 主进程编译：`npm run electron:build-main` 通过。
- 已执行桌面安装包构建：`npm run desktop:dist` 通过。
- 已执行敏感信息扫描：命中项仅为历史日志和安全校验规则说明，未发现真实 API Key、Bearer token、x-api-key 或 GitHub token。
- 工作区修改文件符合 v0.6-E 范围：`build/icons/icon.ico`、`build/icons/icon.png`、`docs/DESKTOP_RELEASE.md`、`src/App.tsx`、`src/styles.css`、`src/assets/suoyi-icon.png`。
- `release-v06d`、`dist`、`dist-electron` 等构建产物不进入源码提交；GitHub Release 上传需单独确认后执行。

## 2026-06-29 v0.1.0 GitHub Release 已创建

### 总控发布记录

- 已在 `yuhui4756-hub/ai-companion` 创建正式 Release：`v0.1.0`，标题为“所依 v0.1.0”。
- Release 地址：`https://github.com/yuhui4756-hub/ai-companion/releases/tag/v0.1.0`。
- 已上传三个 Release 资产：`suoyi-setup-0.1.0.exe`、`suoyi-setup-0.1.0.exe.blockmap`、`latest.yml`。
- 已通过 GitHub API 核对远端资产大小和 SHA256，均与本地 `release-v06d` 产物一致。
- 已通过 `gh release download` 下载远端 `latest.yml` 并与本地文件 hash 对比一致。
- 当前仓库可见性为 `PRIVATE`。因此普通未登录公网访问 Release 下载地址会返回 404，桌面应用内不带 GitHub token 的自动更新也不能从该私有仓库直接获取更新。
- 更新器错误脱敏逻辑会把 404/发布源不可用处理为普通提示，不暴露 token、堆栈或敏感参数。
- 若要让其他用户直接下载并让自动更新源可用，需要后续由总控在用户确认后将仓库公开，或改用公开 HTTPS/GitHub Releases 发布源。

## 2026-06-29 仓库公开与 Release 下载验证通过

### 总控发布记录

- 用户确认公开仓库后，已将 `yuhui4756-hub/ai-companion` 从 `PRIVATE` 改为 `PUBLIC`。
- 公开前已扫描当前源码、历史提交、敏感文件名和 GitHub Secrets，未发现真实 `sk-*`、Bearer token、GitHub token、x-api-key 等密钥线索。
- 公开后已验证仓库可见性为 `PUBLIC`，Release 页面 `https://github.com/yuhui4756-hub/ai-companion/releases/tag/v0.1.0` 返回 200。
- 已匿名下载 `latest.yml` 并与本地 `release-v06d/latest.yml` hash 对比一致。
- 已验证 `suoyi-setup-0.1.0.exe` 和 `suoyi-setup-0.1.0.exe.blockmap` 下载地址返回 200，公开下载源已可用。
- 已更新 `README.md`，将公开安装包下载入口、v0.1.0 Release 页面、桌面版状态、自动更新边界和本地数据说明同步到当前发布状态。

## 2026-06-29 v0.1.1 自动更新链路验证通过

### 总控发布记录

- 已将源码版本升级到 `0.1.1`，并提交推送：`1c25d59 Prepare Suoyi v0.1.1 update test`。
- 已重新构建 Release 资产：`release-v06d/suoyi-setup-0.1.1.exe`、`release-v06d/suoyi-setup-0.1.1.exe.blockmap`、`release-v06d/latest.yml`。
- 已创建公开 GitHub Release：`https://github.com/yuhui4756-hub/ai-companion/releases/tag/v0.1.1`。
- 已上传三个 Release 资产：`suoyi-setup-0.1.1.exe`、`suoyi-setup-0.1.1.exe.blockmap`、`latest.yml`。
- 已验证 `latest.yml` 可从公开 Release 地址读取，内容版本为 `0.1.1`，指向 `suoyi-setup-0.1.1.exe`。
- 已从本地隔离目录安装 `v0.1.0`，运行后通过桌面更新桥接检测到 `v0.1.1`，状态为 `available`。
- 已触发更新下载，状态变为 `downloaded`。
- 已触发重启安装，重新启动后桌面桥接返回 `version: 0.1.1`，更新状态为 `not-available`。
- 升级前写入的本地测试 marker 在升级后仍可读取，说明同一 appId/userData 下更新未清空本地数据；测试 marker 已清理。
- 用户本机也确认界面显示为 `v0.1.1`。

### 验证命令与边界

- `node scripts/verify-source-index.cjs` 通过。
- `npm run build` 通过。
- `npx tsc --noEmit` 通过。
- `npm run electron:build-main` 通过。
- `npm run desktop:dist` 通过。
- 源码/配置/文档密钥扫描未发现真实 API Key、Bearer token、x-api-key 或 GitHub token。
- `curl.exe` 在本机验证 GitHub 资产时遇到 Windows 证书吊销检查网络错误，但 `gh release view` 与 PowerShell `Invoke-WebRequest` 已验证 Release 元数据和 `latest.yml` 公开可读；真实应用更新下载也已成功。
- 临时测试安装目录 `output/v011-update-test` 已清理；未将 `release-v06d`、`dist`、`dist-electron` 等构建产物提交进源码仓库。

## 2026-06-29 v0.2 channel-adapter + OneBot 本地实验骨架通过

### 测试验收结论

- 测试验收线程 `019ef2fc-69dc-7153-ad81-bad7d7c3b1f3` 已完成 v0.2 channel-adapter + `qq-onebot-local` 实验架构骨架复验。
- 结论：通过。
- 阻塞问题：无。
- 普通问题：无。

### 已通过项摘要

- `ChannelKind` 已包含 `desktop-local`、`qq-onebot-local`、`qq-official-bot`、`wechat-official`。
- 统一 incoming/outgoing/conversation key 类型已包含渠道、用户/会话/伴侣外部 ID、`contentSegments`、`rawEventSummary` 等字段。
- `src/channel-adapter/onebotLocal.ts` 已提供默认配置、mock 事件生成、OneBot 事件归一化、响应决策、会话隔离 key、outgoing payload preview、token/endpoint 脱敏和状态文案映射。
- mock 纯函数覆盖私聊、群聊 @、群聊未 @、自我消息/echo、重复 `message_id` 去重，均符合预期。
- 设置页新增“OneBot 本地连接（实验）”区域，明确这不是腾讯官方机器人通道，只连接本机 OneBot/NapCat 服务，不保存 QQ 密码、Cookie 或扫码凭证，不代登录。
- 群聊默认策略为关闭；mock 群聊 @ 场景只临时使用 `mention-or-wake`，不改变默认配置。
- mock 输出仅展示 `send_private_msg` / `send_group_msg` payload preview 或 `{ action: "none" }`，没有真实网络发送。
- 本轮未连接真实 NapCat，未要求 QQ 账号、扫码、Cookie 或 token；符合本地实验骨架范围。
- 导出仍只包含配置脱敏摘要、伴侣、记忆和风格摘要，不包含 OneBot access token、QQ 凭证或原始 messages。

### 总控最终确认

- 已执行类型检查：`npx tsc --noEmit` 通过。
- 已执行最终构建：`npm run build` 通过。
- 已执行敏感信息扫描：未发现真实 API Key、Bearer token、x-api-key、GitHub token 或 QQ Cookie 常见字段。
- 工作区修改文件符合 v0.2 OneBot 本地实验骨架范围：`README.md`、`src/App.tsx`、`src/channel-adapter/*`、`src/storage/localStorage.ts`、`src/styles.css`。
- 下一阶段若推进真实 NapCat 联调，必须继续坚持不记录 QQ 密码/Cookie/扫码凭证、不要求用户在线程提供 token、不把 NapCat 打包进安装包、先低频私聊自测。

## 2026-07-20 工程化升级阶段初始化

### 总控初始化记录

- 用户要求使用 `multi-thread-project-orchestrator` skill 启动新线程协作，并由当前线程作为总控。
- 已读取当前项目协作文档：`PROJECT_CONTEXT.md`、`THREAD_REGISTRY.md`、`TASK_HANDOFF.md`、`docs/THREAD_PROMPTS.md`、`docs/TECHNICAL_BLUEPRINT.md`、`docs/MVP_SPEC.md`、`docs/ACCEPTANCE_CHECKLIST.md`。
- 已新增 `docs/PROJECT_ORCHESTRATION.md`，定义本阶段目标、约束和线程职责。
- 已将工程化升级方向写入项目上下文、技术蓝图、产品规格、验收清单和线程提示词。
- 本阶段目标：在不重做现有所依应用的前提下，补足本地后端代理、SQLite 或等价本地持久化、最小本地知识库/RAG。
- 本阶段非目标：云账号、云同步、真实 QQ/微信接入、公开发布、付费系统、记录真实 API Key。

### 新建线程

- 产品经理：`019f7ebc-2835-7d33-80f8-3338d60c8bf4`
- 技术架构：`019f7ebc-6bf6-70a1-9bea-9d533dfce78e`
- 开发实现：`019f7ebc-aca7-7152-bd9e-ed8fa73080b7`
- 测试验收：`019f7ebc-f28f-7f62-b6c5-fdf2339e25b1`
- 记录交接：`019f7ebd-2ad5-7812-9411-f545a80116b2`

### 下一步

- 总控回收产品经理线程的范围和验收标准。
- 若产品交接完整，总控或产品线程将任务包交给技术架构线程。
- 开发实现线程在收到架构任务包前不主动改代码。
- 测试验收线程先准备验收计划，待开发产物完成后执行验收。

### 线程误发纠偏记录

- 发生情况：产品经理线程第一轮在总控更新新阶段登记表前读取到旧 `THREAD_REGISTRY.md`，将工程化升级任务包误发给旧技术架构-v2 线程 `019f134a-40ad-7f72-8703-324aae9fd985`，并指向旧开发线程 `019ef2fc-293f-7991-9245-9cc1b8f110e9`。
- 原因判断：新线程创建、文档更新、线程补充同步存在时序差，专业线程先读到了旧阶段默认交接对象。
- 纠偏动作：总控已通知旧技术架构-v2 线程和旧开发实现线程忽略本轮工程化升级任务，不继续处理、不转发、不改代码。
- 正确流向：产品经理线程已按最新登记表重新输出交接，并把任务包发送给新技术架构线程 `019f7ebc-6bf6-70a1-9bea-9d533dfce78e`。
- 后续要求：本阶段后续任务包必须显式写入 `AI伴侣-工程化-*` 线程标题和线程 ID；旧阶段线程只保留为历史记录。

### 测试验收计划回收

- 来源线程：AI伴侣-工程化-测试验收（`019f7ebc-f28f-7f62-b6c5-fdf2339e25b1`）。
- 完成内容：已准备工程化阶段验收计划，覆盖构建/类型检查、密钥泄漏、本地代理、旧 `localStorage` 迁移、SQLite 或等价本地持久化、RAG 注入/删除、恋爱聊天体验回归、UI 和隐私文档回归。
- 修改文件：无，测试线程只读。
- 验证：测试线程仅执行只读文档和源码基线扫描，未运行构建或功能验收，因为开发实现尚未交付。
- 分级口径：开发分批交付时只验收已声明范围；总控声明 P0 完整交付时才按工程化 P0 全量判定阻塞缺项。
- 下一步：等待技术架构线程交付开发任务包，再由开发实现线程实施；开发完成后将任务包交回测试验收线程执行实际验收。

### 记录交接回收

- 来源线程：AI伴侣-工程化-记录交接（`019f7ebd-2ad5-7812-9411-f545a80116b2`）。
- 完成内容：已只读检查协作文档一致性，确认工程化阶段主线基本一致，并提出最小修订建议。
- 修改文件：无，记录交接线程只读。
- 总控处理：已采纳低风险文档收口建议，更新旧/新阶段区分、交接额外要求、线程提示词措辞、协作流转说明、活跃阶段状态和当前阶段索引。

### 第一轮代理与边界切片验收回收

- 来源线程：AI伴侣-工程化-测试验收（`019f7ebc-f28f-7f62-b6c5-fdf2339e25b1`）。
- 当前阶段：工程化升级第一轮开发产物验收完成，按“代理与边界先落地”切片验收，不按 P0 完整交付判定 SQLite/UI 知识库导入/RAG 自动注入等后续项。
- 完成内容：静态核对桌面模型请求链路、Electron preload 白名单、主窗口安全基线、主进程代理错误码和脱敏、repository/RAG 骨架；用 Playwright/Chrome headless 做轻量 Web 回归。
- 修改文件：无，测试线程只运行验证；构建和 Playwright 产生的本地快照/日志未进入源码变更。
- 验证结果：`npx tsc --noEmit`、`npm run build`、`npm run desktop:build` 均通过；窄密钥扫描无真实 secret 命中；宽敏感词命中均为脱敏正则、历史日志/文档说明、设置页隐私文案等，经人工复核未发现真实 API Key/token/Cookie/扫码凭证。
- 阻塞问题：无。
- 普通问题：首次新环境点击“先用默认女友”后，侧栏出现两个同名“予安”（一个 onboarding 新建伴侣，一个默认 romance 伴侣）。不影响本轮代理/边界切片主目标，但会造成首次体验困惑。
- 可后续优化：为主进程代理补自动化/mock IPC 测试；后续补 RAG 动态函数测试、SQLite/持久化迁移验收、桌面运行态 IPC 路径 E2E。
- 通过结论：本轮“代理与边界先落地”切片通过验收；不是工程化 P0 全量通过。
- 总控处理：将重复“予安”作为普通体验问题退回工程化开发实现线程处理；下一轮仍建议推进 SQLite/持久化迁移和可操作知识库入口。

### 重复“予安”普通问题复验关闭

- 来源线程：AI伴侣-工程化-测试验收（`019f7ebc-f28f-7f62-b6c5-fdf2339e25b1`）。
- 当前阶段：普通体验问题复验完成。
- 完成内容：复核 `src/App.tsx` 小范围修复，`skipOnboarding()` 已从创建新的 onboarding 女友伴侣改为复用默认 `companion-romance`。
- 验证结果：新浏览器上下文清空 `localStorage` 后，打开 Web、点击“知道了”、点击“先用默认女友”，侧栏主列表只显示 1 个“予安”；`ai-companion:active-companion-id` 为 `companion-romance`；`ai-companion:companions` 中没有新生成的 `source:"onboarding"` 伴侣；onboarding 状态为 `skipped`。
- 兼容回归：点击“更多”可打开伴侣管理，显示 1 个主列表恋爱伴侣和 4 个兼容旧伴侣；临时注入 `source:"manual"` 自定义伴侣并重载后，页面未强行打开 onboarding，也未被默认女友逻辑覆盖。
- 验证命令：`npx tsc --noEmit` 通过；`npm run build` 通过；窄密钥扫描无真实 secret 命中；Playwright CLI 复验通过，控制台 0 errors、0 warnings。
- 阻塞问题：无。
- 普通问题：无，上一轮重复“予安”问题已关闭。
- 可后续优化：本修复不自动清理旧 bug 已经产生的同名 onboarding 伴侣，避免误删用户数据；如后续需要，可单独设计可见、可撤销的数据清理/合并入口。
- 总控处理：记录该普通问题已关闭；下一步交给技术架构线程切分第二轮 SQLite/迁移/RAG UI 与注入任务包。

### 第二轮方向校准：Python 本地后端

- 来源：用户确认。
- 背景：用户提醒项目还需要服务于简历表达，当前主项目并非 Python 实现；总控建议不要虚构技术栈，而是在后续工程化切片中加入真实可运行的 Python 后端模块。
- 总控决策：第二轮优先让技术架构线程按 Python/FastAPI 本地服务方向设计，形成“React/Electron 客户端 + Python 本地后端”的可展示架构。
- 目标边界：Python 服务优先承接模型代理、SQLite 持久化、旧 `localStorage` 迁移脚本、知识库/RAG 检索中的最小可验收闭环；不得记录真实 API Key，不删除用户真实数据，不引入云账号或云同步。
- 任务包状态：已发送给技术架构线程 `019f7ebc-6bf6-70a1-9bea-9d533dfce78e`，要求其产出第二轮开发任务包并交给工程化开发实现线程。

### 2A Python 本地知识库/RAG + SQLite 服务验收回收

- 来源线程：AI伴侣-工程化-测试验收（`019f7ebc-f28f-7f62-b6c5-fdf2339e25b1`）。
- 当前阶段：工程化第二轮 2A Python 本地知识库/RAG + SQLite 服务切片验收完成；不是工程化 P0 全量通过。
- 完成内容：已验收 Python/FastAPI 本地后端健康检查、SQLite 初始化和状态、知识库导入/列表/重复导入/检索/软删除；已验收 React UI 顶部“知识”入口、后端连接状态、Markdown 导入、列表元数据、重复导入提示、刷新后持久化、删除后不再检索；已验收聊天发送前 RAG 注入、无命中不注入、删除后不注入、后端搜索失败时聊天不崩并跳过 RAG。
- 验证结果：`./.venv/Scripts/python -m pytest backend/tests` 通过（4 passed，1 个 FastAPI/Starlette TestClient 的 httpx 弃用 warning）；`npx tsc --noEmit`、`npm run build`、`npm run desktop:build` 均通过；`/health` 返回 `status: ok`、`dbReady: true`、`schemaVersion: 1`；HTTP API、Playwright UI、fake OpenAI route 和密钥扫描均通过。
- 数据与隐私影响：Python 后端只接收最新用户输入用于本机检索，只保存知识库 sources/chunks 到本机 SQLite，不接收、不保存、不转发模型 API Key；模型请求仍会把用户输入、聊天上下文、长期记忆和命中知识片段发给用户配置的模型服务商。
- 阻塞问题：无。
- 普通问题：`PROJECT_CONTEXT.md` 仍写“当前没有后端服务器、数据库持久化层、向量检索或 RAG 知识库能力”，与 2A 已交付状态不一致。
- 总控处理：已更新 `PROJECT_CONTEXT.md` 当前实现状态，明确 2A 已有 Python/FastAPI sidecar、SQLite 知识库和 RAG 注入，同时保留核心数据尚未迁入 SQLite 的边界。
- 可后续优化：后续 2B 继续推进核心数据 SQLite 迁移、legacy snapshot 事务导入、Electron 自动拉起 Python sidecar、健康重连和安装包集成；知识库检索可继续增强分词、命中解释或 embedding。

### 2A 总控最终确认与提交

- 总控复核：`./.venv/Scripts/python -m pytest backend/tests` 通过；`npx tsc --noEmit` 通过；`npm run build` 通过；`npm run desktop:build` 通过；严格密钥形态扫描无命中。
- 后端健康检查：`/health` 返回 `status: ok`、`dbReady: true`、`schemaVersion: 1`；本机 8765 端口已有服务监听，因此未强行停止或替换运行中的服务。
- 提交推送：已提交并推送到 `origin/main`，提交 `680d6d0 Add local Python knowledge backend`。
- 桌面更新边界：本轮只提交源码，不发布新的 GitHub Release 或桌面安装包；当前线上安装包版本仍为 `0.1.1`，所以已安装桌面端不会提示更新。Python sidecar 尚未被 Electron 自动托管，直接发布桌面自动更新会让用户获得半成品体验，需在 2B 解决安装、启动和更新边界后再发布新版。

### 2B 启动：核心数据迁移与桌面 sidecar

- 总控决策：继续下一步，先由技术架构线程切分 2B 任务。
- 目标方向：核心数据 SQLite 迁移、legacy `localStorage` snapshot 事务导入、Electron 托管 Python sidecar、健康重连、安装包/自动更新发布边界。
- 任务包状态：已发送给技术架构线程 `019f7ebc-6bf6-70a1-9bea-9d533dfce78e`，要求其产出开发实现任务包并交给工程化开发实现线程。

### 2B 核心数据迁移与 Electron sidecar 验收回收

- 来源线程：AI伴侣-工程化-测试验收（`019f7ebc-f28f-7f62-b6c5-fdf2339e25b1`）。
- 当前阶段：工程化第二轮 2B 测试验收完成，范围为核心数据 SQLite 迁移与 Electron 托管 Python sidecar；不是工程化 P0 全量通过。
- 完成内容：已验收 Python/FastAPI schema v2 的 `/health`、`/db/status`、`/core/status`、`/core/snapshot`、`PUT /core/snapshot`、`POST /core/migrations/local-storage-snapshot`；已用独立临时 SQLite 验证 companions/messages/memories/style_summaries/provider config 写入读回、重复迁移不重复插入、缺失 message id 派生稳定 id、重启后可读回 snapshot。
- 隐私边界：renderer 构造 core snapshot 时去掉 `apiKey`；后端即使收到带假密钥形态的字段也会脱敏；SQLite provider_configs 只保留 `api_key_ref=renderer-localStorage`，未发现真实密钥入库、入日志或入扫描结果。
- UI 与回归：Web UI 首次默认女友仍只显示 1 个“予安”；知识 UI 导入、持久化、重复提示、RAG 注入、软删除后不注入、后端停止 fallback 均通过；记忆面板不混入知识 marker。
- Electron sidecar：开发态 8765 空闲时托管后端并返回 schema v2；8765 被占用时落到 8766；关闭 Electron 窗口后对应 sidecar 端口释放；最终 8765-8780 无监听，Electron/uvicorn 无残留。
- 验证结果：`./.venv/Scripts/python -m pytest backend/tests` 通过（6 passed，1 个 FastAPI/Starlette TestClient 的 httpx 弃用 warning）；`npx tsc --noEmit`、`npm run build`、`npm run desktop:build` 通过；严格密钥形态扫描无命中；宽敏感词扫描人工复核未见真实 API Key/token/Cookie/扫码凭证。
- 阻塞问题：无。
- 普通问题：阶段文档仍停在 2A/等待 2B，需同步 `PROJECT_CONTEXT.md` 与 `docs/PROJECT_ORCHESTRATION.md`。
- 总控处理：已同步项目上下文和编排状态，明确 2B 已完成 core snapshot/SQLite 迁移与 Electron dev sidecar，同时标注公开安装包仍未内置 Python 可执行文件和 backend resources，发布/自动更新留到 2C。
- 可后续优化：2C 单独设计 PyInstaller/资源打包/升级/回滚；补 core migration、Electron sidecar 端口回退、preload 白名单、RAG 注入/删除自动化测试；后续可增加核心数据细粒度 CRUD、恢复/清理 UI、SQLite 加密或 OS 安全存储。

### 2B 总控最终确认与提交

- 总控复核：`./.venv/Scripts/python -m pytest backend/tests` 通过（6 passed，1 个 FastAPI/Starlette TestClient 的 httpx 弃用 warning）；`npx tsc --noEmit` 通过；`npm run build` 通过；`npm run desktop:build` 通过；严格密钥形态扫描无命中。
- 提交推送：已提交并推送到 `origin/main`，提交 `a3d6acd Add core SQLite migration and Electron sidecar`。
- 2C 路由：已发送任务给技术架构线程 `019f7ebc-6bf6-70a1-9bea-9d533dfce78e`，要求其切分公开安装包内置 Python resources、PyInstaller/资源打包、自动更新、升级回滚和发布验收任务包。

## 2026-07-21 工程化 2C 本地候选资产验收

### 2C 发布打包与 Python sidecar 资源内置验收回收

- 来源线程：AI伴侣-工程化-测试验收（`019f7ebc-f28f-7f62-b6c5-fdf2339e25b1`）。
- 当前阶段：工程化 2C 测试验收完成，范围为发布打包与 Python sidecar 资源内置；本轮仅验收本地候选资产，不公开发布，不代表工程化 P0 全量完成。
- 验收结论：2C 本地候选资产切片通过验收；阻塞问题无，普通问题无。
- 完成内容：`npm run desktop:dist` 已覆盖 `backend:build-sidecar`、Web 构建、Electron main 构建和 `electron-builder --win nsis --publish never`；生成 `backend/dist/suoyi-backend/suoyi-backend.exe`，并把 packaged 候选所需资源放入 `release-v06d/win-unpacked/resources/python-backend/`。
- 候选资产：`release-v06d/win-unpacked/resources/python-backend/suoyi-backend.exe`、`suoyi-setup-0.1.1.exe`、`.blockmap`、`latest.yml` 均存在；`latest.yml` 仅含本地文件名、sha512、size、releaseDate，无 token。
- Packaged sidecar 验收：正常 packaged run 下 8765 `/health` 返回 schema v2；8765 被占用时自托管 sidecar 落到 8766；关闭窗口后对应端口释放；缺失 `suoyi-backend.exe` 时主窗口仍可打开并 fallback，未启动新 sidecar；最终 8765-8780、Electron、所依、`suoyi-backend` 均无本轮残留。
- 2A/2B 回归：packaged resources 内 sidecar 的 knowledge API 导入、重复 409、相关检索、软删除后无命中均通过；core migration 幂等、snapshot 读回、去 Key provider config 和 SQLite 隐私边界均通过；Web UI 默认“予安”不重复、无后端 fallback、知识 UI 导入/删除回归通过。
- 隐私与安全：未索要、未使用、未记录真实 API Key/token/Cookie/扫码凭证/GitHub token；Python sidecar 仍不接收、不保存、不转发模型 API Key；源码和 release 严格 token 形态扫描 0 命中。
- 可后续优化：PyInstaller 构建仍有 `Hidden import "tzdata" not found` warning，但 sidecar exe、packaged normal、端口冲突、API smoke 均通过，当前不阻塞；后续若引入依赖时区数据的能力，再显式补 hidden import 或依赖说明。
- 发布边界：当前候选包版本仍是 `0.1.1`，符合“不 bump version、不公开发布”的任务边界；正式公开发布前仍需总控和用户确认版本号、GitHub Release 上传、自动更新链路、安装/升级路径数据保留，以及代码签名/SmartScreen 边界。

### 2C 总控最终确认

- 总控复核：`./.venv/Scripts/python -m pytest backend/tests` 通过（6 passed，1 个 FastAPI/Starlette TestClient 的 httpx 弃用 warning）；`npm run desktop:dist` 通过，并明确使用 `electron-builder --win nsis --publish never`；严格密钥形态扫描无命中；`git diff --check` 无 whitespace error。
- 候选资产确认：`release-v06d/suoyi-setup-0.1.1.exe`、`.blockmap`、`latest.yml` 和 `release-v06d/win-unpacked/resources/python-backend/suoyi-backend.exe` 已生成；构建产物、PyInstaller 产物、测试输出和 SQLite 数据均为 ignored 本地文件，不进入源码提交。
- 总控决策：本轮只提交源码、打包配置、脚本和文档，不 bump version、不上传 GitHub Release、不公开发布；是否进入 2D 正式发布准备需要用户确认。

### 2D 发布准备启动

- 来源：用户确认可以继续。
- 当前远端发布状态：GitHub Releases 最新仍为 `v0.1.1`，本轮 2C 候选资产未上传 Release，已安装桌面端不会收到自动更新提示。
- 总控决策：进入 2D 发布准备/发布验收切分，但正式 bump version、上传 GitHub Release、公开发布和自动更新端到端执行仍需总控最终确认。
- 任务包状态：已发送给技术架构线程 `019f7ebc-6bf6-70a1-9bea-9d533dfce78e`，要求其切分版本号、安装/升级路径、旧 userData 数据保留、GitHub Release artifacts、自动更新验证、代码签名/SmartScreen 文案和回滚边界。

### 2D 发布准备材料与候选核验复验回收

- 来源线程：AI伴侣-工程化-测试验收（`019f7ebc-f28f-7f62-b6c5-fdf2339e25b1`）。
- 当前阶段：工程化 2D 发布准备与发布验收支撑复验；本轮只验发布前文档、核验脚本和本地候选资产，不公开发布，不代表工程化 P0 全量完成。
- 验收结论：2D 发布准备材料与本地候选资产核验通过；阻塞问题无，普通问题无。
- 版本与发布边界：`package.json.version` 和 `package-lock.json` 根包版本均仍为 `0.1.1`；README 下载地址和 Release 页面仍指向 `v0.1.1`；`desktop:dist` 仍使用 `electron-builder --win nsis --publish never`；本轮未创建、修改、删除或上传 GitHub Release。
- 核验脚本：`scripts/verify-release-candidate.ps1 -ExpectedVersion 0.1.1` 通过，确认 installer、blockmap、`latest.yml`、packaged sidecar 存在，且 `latest.yml` version/path/url/size/sha512 与目标 installer 一致；脚本只读检查本地候选资产，不调用发布命令，不读取或打印 `GH_TOKEN`。
- 验证结果：`./.venv/Scripts/python -m pytest backend/tests` 通过（6 passed，1 个 Starlette/FastAPI TestClient deprecation warning）；`npx tsc --noEmit`、`npm run build`、`npm run desktop:build` 通过；`git diff --check` 无 whitespace error；源码和 release 严格 token 形态扫描 0 命中。
- Packaged smoke：使用临时 `APPDATA/LOCALAPPDATA` 启动 `release-v06d/win-unpacked/所依.exe`，内置 sidecar 在 8765 返回 `/health status=ok dbReady=true schemaVersion=2`；关窗后 app 退出、8765 释放、无候选 app/sidecar 残留；未删除用户真实 localStorage、SQLite、backend/data 或 Electron userData。
- 可后续优化：`release-v06d/` 仍保留历史本地资产 `suoyi-setup-0.1.0.exe` 与 `.blockmap`，当前不影响通过，因为脚本按 `ExpectedVersion` 精确校验目标资产；后续可让核验脚本对非目标版本 installer/blockmap 给出 warning 或 fail，降低人工误选上传风险。
- 发布边界：正式公开发布前仍需总控确认版本 bump、重新生成 `0.1.2` 候选包、远端 GitHub Release 上传、自动更新端到端、安装/升级路径数据保留、代码签名/SmartScreen 文案；这些不属于本轮 2D 通过结论。

### 2D 总控最终确认

- 总控复核：`scripts/verify-release-candidate.ps1 -ExpectedVersion 0.1.1` 通过；`./.venv/Scripts/python -m pytest backend/tests` 通过（6 passed，1 个 Starlette/FastAPI TestClient deprecation warning）；`npm run desktop:build` 通过；严格密钥形态扫描无命中；`git diff --check` 无 whitespace error。
- 远端边界：本轮前段只读查询 GitHub Releases 显示最新仍为 `v0.1.1`；后续复查遇到 GitHub GraphQL TLS/EOF 网络错误，未执行任何创建、上传、修改或删除 Release 的动作。
- 总控决策：本轮只提交 2D 发布准备文档和本地候选核验脚本；不 bump version，不上传 GitHub Release，不公开发布。下一步若用户确认正式发布，再单独进入 `v0.1.2` 发布执行与发布验收。

## 2026-07-21 v0.1.2 正式发布执行

### 发布执行与远端验收

- 来源：用户确认可以进入正式发布执行。
- 版本提交：已将 `package.json` 和 `package-lock.json` 根包版本升级到 `0.1.2`，同步 `README.md`、`PROJECT_CONTEXT.md`、`docs/DESKTOP_RELEASE.md`、`docs/PROJECT_ORCHESTRATION.md`，并提交推送 `44c798f Prepare Suoyi v0.1.2 release` 到 `origin/main`。
- 发布 tag：已创建并推送 `v0.1.2`，指向提交 `44c798f4d4aca30cefa29251c446359af2eeb0f4`。
- 本地发布前验证：`./.venv/Scripts/python -m pytest backend/tests` 通过（6 passed，1 个 Starlette/FastAPI TestClient deprecation warning）；`npm run desktop:dist` 通过；`scripts/verify-release-candidate.ps1 -ExpectedVersion 0.1.2` 通过；源码和 release 严格密钥形态扫描无命中；`git diff --check` 无 whitespace error，仅 Windows CRLF 提示。
- 本机上传情况：先尝试用 `gh release create/upload` 上传本地 `suoyi-setup-0.1.2.exe`，多次被远端断开；未形成公开半成品 Release，后续保留空草稿并改用 GitHub Actions。
- 发布 workflow：新增并推送 `28f998e Add manual desktop release workflow`；手动触发 `Release desktop` workflow，run `29810653064` 成功完成，步骤包含 checkout tag、安装依赖、后端测试、`npm run desktop:dist`、候选核验和资产上传发布。
- 公开 Release：`https://github.com/yuhui4756-hub/ai-companion/releases/tag/v0.1.2` 已发布，状态为非 draft、非 prerelease，发布时间 `2026-07-21T07:32:21Z`。
- 远端资产：`latest.yml` 339 bytes；`suoyi-setup-0.1.2.exe` 106352683 bytes；`suoyi-setup-0.1.2.exe.blockmap` 109952 bytes，三者均为 uploaded 状态。
- 远端下载验收：公开 `latest.yml` 可下载，内容为 `version: 0.1.2`、`path: suoyi-setup-0.1.2.exe`、`size: 106352683`；公开 installer URL `HEAD` 返回 200。
- 数据与隐私：未索要、未使用、未记录真实 API Key/token/Cookie/扫码凭证；发布 token 仅由本机 GitHub CLI/Actions 环境使用，未写入源码、文档、日志、`latest.yml` 或安装包；Release 资产不包含用户 SQLite、`.env`、`.venv` 或 `backend/data`。
- 未完成边界：未在用户真实安装环境执行 `v0.1.1 -> v0.1.2` 自动更新端到端，因为这会安装/覆盖本机应用并触碰真实 userData；若继续验收，应单独以可回退、可识别 marker 的方式执行。

## 2026-07-22 RAG-Q1 质量升级验收

### RAG-Q1 结构化切片与 FTS5/BM25 基线验收回收

- 来源线程：AI伴侣-工程化-测试验收（`019f7ebc-f28f-7f62-b6c5-fdf2339e25b1`）。
- 当前阶段：RAG-Q1 质量升级验收，范围为结构化切片、FTS5/BM25 基线检索和 prompt 注入门槛；本轮不是远程 embedding/hybrid 完成，也不代表 RAG 高准确率已最终完成。
- 验收结论：通过，阻塞问题无。
- 完成内容：开发实现线程完成 schema v3、结构化知识切片、FTS5/BM25 基线、低置信/泛字段 query 的 `shouldInject=false` 与 `needsClarification=true`、旧库非破坏性迁移回填、FTS 不可用时关键词 fallback，以及前端知识库检索响应字段适配。
- 修改文件：`README.md`、`backend/README.md`、`backend/app/db.py`、`backend/app/knowledge.py`、`backend/app/main.py`、`backend/app/schemas.py`、`backend/tests/test_knowledge.py`、`backend/tests/test_rag_quality.py`、`src/backend/pythonBackendClient.ts`。
- 验证结果：`./.venv/Scripts/python -m pytest backend/tests` 通过（12 passed，1 个 FastAPI/Starlette TestClient 的 httpx 弃用 warning）；`npx tsc --noEmit`、`npm run build`、`npm run desktop:build`、`npm run backend:build-sidecar`、`npm run desktop:dir`、`npm run desktop:dist` 均通过；`scripts/verify-release-candidate.ps1 -ExpectedVersion 0.1.2` 通过；源码和 release 严格密钥形态扫描 0 命中；`git diff --check` 无 whitespace error。
- RAG 质量烟测：临时 SQLite 导入 6 份质量夹具后，泛问题“预算金额是多少？”和“负责人是谁？”不注入 prompt 且要求澄清；无关问题空命中；明确编号 `XLP-2026-041` top1 命中目标资料；指定资料问题只注入该资料；软删除后同类 query 0 hits 且空 `promptContext`。
- 结构化切片与迁移：`knowledge_chunks` 新增 `heading_path`、`chunk_type`、`content_hash`、`chunker_version`、`token_estimate`、`metadata_json`、`search_text`；Markdown 切片覆盖 `fact_block/list/table_block/qa`；旧库初始化到 schema v3 不破坏旧 source/chunk，首次检索前可回填检索元数据。
- 数据与隐私：验收只使用临时 SQLite 与假/测试数据，未读取、导出、删除用户真实 localStorage、SQLite、Electron userData 或知识库资料；未索要、未使用、未记录真实 API Key/token/Cookie/GitHub token；未触发真实模型请求。
- 普通问题：`backend/README.md` 的桌面候选资产 smoke 片段仍停在 `0.1.1` 候选包表述，与当前 `0.1.2` 公开状态不一致。
- 总控处理：已同步 `backend/README.md` 为 `0.1.2` 公开后的发布核验口径；该文档问题关闭。
- 可后续优化：远程 embedding/hybrid fusion、召回解释 UI、持续 RAG 质量评测基准、PyInstaller `tzdata` warning 清理、正式签名/自动更新端到端验收仍按后续阶段推进。

## 2026-07-22 RAG-H1 远程 embedding 与 hybrid retrieval 验收

### RAG-H1 测试验收回收

- 来源线程：AI伴侣-工程化-测试验收（`019f7ebc-f28f-7f62-b6c5-fdf2339e25b1`）。
- 当前阶段：RAG-H1 远程 embedding 隐私门控、SQLite 向量索引与 hybrid retrieval 最小闭环验收；本轮不是 RAG 高准确率最终完成，也不是工程化 P0 全量完成。
- 验收结论：通过，阻塞问题无。
- 完成内容：schema v4 非破坏性升级、embedding 配置去 Key 保存、mock/OpenAI-compatible provider 边界、索引状态与重建、hybrid retrieval、Q1 泛字段门槛、软删除不召回、前端远程向量默认关闭与 Key 隔离、聊天发送前按条件携带 embedding runtime config。
- 修改文件：`README.md`、`backend/README.md`、`backend/app/db.py`、`backend/app/embeddings.py`、`backend/app/knowledge.py`、`backend/app/main.py`、`backend/app/schemas.py`、`backend/tests/test_embeddings.py`、`backend/tests/test_knowledge.py`、`scripts/build-python-sidecar.ps1`、`src/App.tsx`、`src/backend/pythonBackendClient.ts`、`src/storage/localStorage.ts`、`src/styles.css`、`src/types.ts`。
- 验证结果：`./.venv/Scripts/python -m pytest backend/tests -q` 通过（19 passed，1 个 Starlette/httpx deprecation warning）；`npx tsc --noEmit`、`npm run build`、`npm run desktop:build`、`npm run backend:build-sidecar`、`npm run desktop:dir`、`npm run desktop:dist` 均通过；`scripts/verify-release-candidate.ps1 -ExpectedVersion 0.1.2` 通过；packaged sidecar smoke 返回 schemaVersion 4；密钥/隐私扫描未发现真实 API Key/token/Cookie/GH_TOKEN；构建产物未混入 SQLite、`.env`、`.venv`、`backend/data` 或测试 fixture。
- H1 API 与 UI 验收：默认 embedding 关闭时搜索不使用 embedding；保存 config 不返回也不入库 apiKey；mock reindex 幂等；vectorReady 后 hybrid 语义改写命中目标资料；泛字段仍不调用 embedding 且不注入；provider 报错时脱敏并降级本地检索；模型/维度变化会标记 stale 并可重建；软删除 source 后 vector 不召回；知识面板展示 schema v4、远程向量状态、单独 Key、测试连接、重建索引和索引计数。
- 数据与隐私：验收只使用临时 SQLite、mock/fake provider 和假 Key 字符串；未请求、未使用、未记录真实 API Key/token/Cookie/GH_TOKEN；未读取、导出、删除用户真实 localStorage、SQLite、Electron userData 或知识库资料。Python 后端仍不接收聊天模型 API Key；embedding Key 仅作为 runtime config 由 renderer 在用户开启并具备 Key 时传入，不写入 SQLite、导出、候选资产或日志。
- 普通问题：`scripts/verify-release-candidate.ps1` 当前只校验 packaged sidecar 文件存在和 release 目录敏感文件/密钥形态，不会主动启动 sidecar 检查 `/health schemaVersion`。测试验收已手动发现并通过重跑 `desktop:dir`/`desktop:dist` 修正本地候选资源到 schemaVersion 4；建议后续把 packaged sidecar schema smoke 纳入发布核验脚本或交接必跑项。
- 总控处理：普通问题不阻塞 H1，本轮先记录为后续发布核验增强项，不在总控最终确认中绕过开发/测试流程直接改脚本。
- 可后续优化：真实远程 embedding provider 端到端、索引任务 UX、向量隐私管理、命中解释 UI、持续 RAG 质量评测基准、大知识库性能、PyInstaller `tzdata` warning 清理、正式签名/发布链路仍按后续阶段推进。

### RAG-H1 发布候选核验脚本普通问题复验关闭

- 来源线程：AI伴侣-工程化-测试验收（`019f7ebc-f28f-7f62-b6c5-fdf2339e25b1`）。
- 当前阶段：RAG-H1 后普通问题修复复验，范围为 `scripts/verify-release-candidate.ps1` 增强 packaged Python sidecar schema smoke，以及 `backend/README.md`、`docs/DESKTOP_RELEASE.md` 文档同步。
- 验收结论：通过。上一轮普通问题“候选核验脚本只检查 packaged sidecar 文件存在、不启动校验 schema”已关闭。
- 完成内容：脚本新增 `ExpectedSchemaVersion` 参数，未传入时可从 `backend/app/db.py` 推断；启动 `release-v06d/win-unpacked/resources/python-backend/suoyi-backend.exe` 到本机临时端口，使用 `%TEMP%/suoyi-release-sidecar-smoke-*` 临时 SQLite，校验 `/health status=ok`、`dbReady=true`、`schemaVersion >= ExpectedSchemaVersion`，并校验 `/db/status` 包含 `ftsReady` 与 `knowledgeSearchMode`。
- 验证结果：显式 `-ExpectedSchemaVersion 4` 通过；默认 schema 推断通过；负向 `-ExpectedSchemaVersion 5` 按预期失败并清理临时目录/端口；`pytest backend/tests -q`、`npx tsc --noEmit`、`npm run build`、`npm run desktop:build` 和 `git diff --check` 均通过。
- 数据与隐私：脚本只使用临时 SQLite，不读取或删除用户真实 localStorage、SQLite、Electron userData 或知识库资料；未上传 Release、未 bump version、未触发真实自动更新；密钥扫描未发现真实 API Key/token/Cookie/GH_TOKEN。
- 总控处理：记录普通问题关闭；本轮只提交脚本和文档收口，不公开发布。
