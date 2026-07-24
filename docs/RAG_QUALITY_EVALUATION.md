# RAG 质量评测

本文记录所依本地知识库的可复现质量评测方式。目标不是证明 RAG 已经达到最终高准确率，而是把切片、检索、向量融合和 prompt 注入的关键风险固定成测试。

## 当前评测范围

当前自动化评测使用本地临时 SQLite、合成 Markdown/文本资料和 mock embedding provider，不使用真实用户资料，也不调用真实远程 embedding 或聊天模型服务。后续真实 provider 评测可优先使用本地 Ollama embedding，再按需要补远程 OpenAI 兼容 provider 对照。

已覆盖的质量门槛：

- 相似资料之间不混答，例如“晨星会员方案”和“晨星硬件巡检”都有上线窗口、预算和负责人，但指定来源的问题只能注入目标资料。
- 常见口语字段可识别，例如“什么时候上线”“花多少钱”“优惠码是什么”。
- 泛字段问题不强行注入，例如只问“上线窗口是什么？”时要求澄清。
- 无关问题不注入知识库资料。
- Markdown 结构化切片要把同一档案里的编号、上线窗口、预算和负责人保留在同一个 fact block。
- 同一 source 下只有弱相关的附加片段不会被塞进 prompt，避免把旁支安全段落或干扰段落混进当前回答。
- mock hybrid retrieval 可覆盖语义改写类问题，例如“用户要退钱时售后开头要先做什么？”应命中退款升级 SOP。
- 类真实资料形态基准包含 12 份核心不敏感 Markdown 文档、24 份相似结构干扰文档和 143 个问题，其中 123 个问题覆盖本地 BM25/关键词检索、泛字段澄清、无关问题和大资料量干扰，20 个问题覆盖 mock hybrid 语义改写。
- 本地 Ollama `bge-m3` 真实 embedding smoke 会在临时 SQLite 中索引同一批 36 份资料，验证本机 hybrid retrieval 在真实中文 embedding 下不会出现过召回、混源或字段值漏注入。

## 运行命令

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_rag_h2_quality.py -q
.\.venv\Scripts\python -m pytest backend\tests\test_rag_realistic_benchmark.py -q
.\.venv\Scripts\python -m pytest backend\tests -q
.\.venv\Scripts\python scripts\rag_benchmark_report.py
.\.venv\Scripts\python scripts\rag_answer_benchmark.py --limit 20 --chat-model deepseek-r1:1.5b --num-predict 320 --allow-failures
.\.venv\Scripts\python scripts\rag_answer_benchmark.py --limit 20 --chat-provider openai-compatible --chat-base-url https://api.deepseek.com --chat-model deepseek-v4-flash --chat-thinking enabled --num-predict 640 --allow-failures
```

## 当前结论

RAG-H2 第一轮已经具备可重复的检索质量基准。它证明的是“检索出来并注入给模型的资料更干净”，不是证明“真实模型最终回答一定正确”。

可记录的阶段数据：

- 48 题 pilot 基准：优化前 37/48 通过，pass rate 为 77.1%。
- 48 题 pilot 基准：优化后 48/48 通过，pass rate 为 100.0%。
- 当前扩展基准：36 份合成 Markdown 资料，143/143 通过，pass rate 为 100.0%；其中 lexical/FTS 为 123/123，hybrid/mock embedding 为 20/20。
- 本地 Ollama `bge-m3` 实测：同一 36 份资料、96 个切片、143 个问题，143/143 通过，pass rate 为 100.0%；其中 lexical/FTS + Ollama auto 为 123/123，hybrid/Ollama 为 20/20，clarify/no-answer 均为 100.0%。
- 推荐对外表述：构建 RAG 检索与 prompt 注入评测体系，将 48 题 pilot benchmark pass rate 从 77.1% 提升到 100.0%，并扩展到 36 份资料、143 题合成基准，覆盖字段问答、表格切片、大资料量干扰、无答案澄清和语义改写；本地 Ollama `bge-m3` hybrid 检索在该基准上达到 100.0% 检索与 prompt 注入通过率；删除后不召回由自动化回归单独覆盖。
- 表述边界：上述数据是自建合成基准上的检索与 prompt 注入通过率，不是线上真实用户问题或真实大模型最终回答准确率。

## 最终回答正确率基线

为了区分“RAG 检索是否把资料给对”和“聊天模型是否真的按资料答对”，新增 `scripts/rag_answer_benchmark.py` 作为端到端回答评测脚本。它会使用同一批合成资料先做知识库检索，再把 `promptContext` 和问题发给本地 Ollama 聊天模型，并按关键事实、禁止混入字段和资料不足表达进行自动评分。

2026-07-24 小模型 smoke 基线：

- embedding：本地 Ollama `bge-m3`。
- chat：本地 Ollama `deepseek-r1:1.5b`，`think=false`，`num_predict=320`。
- 范围：从 143 个问题中抽取 20 个，覆盖明确注入、泛字段澄清、无答案和 hybrid 语义改写。
- 检索门：20/20 通过，pass rate 为 100.0%。
- 最终回答：12/20 通过，pass rate 为 60.0%。

失败主要来自聊天模型行为，而不是检索未命中：小模型有时在没有知识库资料时仍按常识编答案，有时只答大意但漏掉关键原词，例如“核对订单号”“完整 API Key”“先接住情绪”。因此当前可对外表述为：已经建立最终回答正确率评测脚本，本地小模型 smoke 中 RAG 检索门保持 100.0%，但 `deepseek-r1:1.5b` 最终回答正确率为 60.0%，说明后续需要更强聊天模型或更严格的回答约束做对照。

同一 20 题远程模型对照：

- `deepseek-v4-flash`，thinking disabled：检索门 20/20，最终回答 17/20，pass rate 为 85.0%。
- `deepseek-v4-pro`，thinking disabled：检索门 20/20，最终回答 17/20，pass rate 为 85.0%。
- `deepseek-v4-flash`，thinking enabled：检索门 20/20，严格自动评分 19/20，pass rate 为 95.0%；剩余 1 题人工复核为语序型 false negative，按更新后的窄归一化离线重评分为 20/20，pass rate 为 100.0%。

完整 143 题远程回答基准：

- `deepseek-v4-flash`，thinking enabled：检索门 143/143，pass rate 为 100.0%。
- 同一批答案原始严格自动评分：132/143，pass rate 为 92.3%。
- 更新评分器后忽略 Markdown/普通标点做窄归一化，离线重评分：133/143，pass rate 为 93.0%。
- 人工复核剩余 10 个失败：4 个属于可接受表达但自动评分没有识别，例如用户问“有几台备用路由器”时回答“2台”，或把“截图是否含 Key”答成“截图里没有 Key”；6 个是真问题，集中在漏掉第二个关键字段、语义改写题只答部分事实、或把有答案的问题误判成资料不足。
- 保守对外表述建议：在 36 份合成资料、143 题基准上，RAG 检索与注入保持 100.0%；接入远程 DeepSeek `deepseek-v4-flash` thinking 后，最终回答自动评分达到 93.0%，人工复核显示主要剩余问题是字段抽取漏项，而不是检索召回错误或无答案乱答。

这组数据仍然是合成基准，不是线上真实用户准确率。后续对比远程大模型时应复用同一脚本和同一题集，优先记录：检索门、最终回答正确率、无答案收口率、漏关键事实率和平均耗时。

当前自动化基准按用例逐条断言：

- top1 source 必须等于期望资料。
- promptContext 必须包含关键答案片段。
- promptContext 不能包含指定干扰片段。
- 泛字段和无关问题必须不注入。

真实回答正确率仍取决于：

- 用户导入资料本身是否完整、清楚、无矛盾。
- 切片是否覆盖更长、更复杂的真实文档结构。
- 真实 embedding provider（本地 Ollama 与远程 OpenAI 兼容接口）对中文、口语改写、短查询和专有名词的表现。
- 聊天模型是否正确使用“用户导入资料”，并在资料不足时愿意澄清。
- 当前导入入口主要面向纯文本和 Markdown；图表、图片、扫描件、PDF/Word 等资料还需要后续解析和结构化策略。

## 下一轮真实数据评测建议

准备一批不含隐私和真实密钥的 Markdown 资料，建议 10-20 篇，每篇 500-3000 字。优先包含：

- 多份字段相同但值不同的资料。
- 表格、问答、列表和长段落混合的资料。
- 很相似的名称、编号、人名或活动名。
- 故意缺失答案的资料，用来测试“不知道/需要澄清”。

问题集建议 30-50 个，分成：

- 明确来源字段题：应该 top1 命中目标资料。
- 口语改写题：测试 hybrid retrieval 是否比纯关键词更稳。
- 干扰题：资料库里有相似字段，但不能混答。
- 无答案题：必须不注入或要求澄清。
- 删除后复问：删除资料后不能召回旧片段。

真实 provider 端到端测试只应在本机 UI 或本机环境里由用户自行填写 Key；不要把完整 API Key 写进 issue、日志、截图、文档或提交记录。
