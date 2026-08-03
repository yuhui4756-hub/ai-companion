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
- 多格式文本层基准覆盖后端 `.txt/.md/.pdf/.docx` 导入：PDF 只验证已有文本层和页码 metadata，DOCX 验证标题、段落、列表和表格行事实块，删除后不召回，泛字段/无关问题不注入。
- 多格式公开资料基准把公开官方文档摘要做成 Markdown/TXT/PDF/DOCX 文件导入，验证文件解析、结构化切片、FTS/BM25、mock hybrid、metadata、表格行和删除后不召回可以在更接近真实文件形态的资料上复用。

## 运行命令

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_rag_h2_quality.py -q
.\.venv\Scripts\python -m pytest backend\tests\test_rag_realistic_benchmark.py -q
.\.venv\Scripts\python -m pytest backend\tests -q
.\.venv\Scripts\python scripts\rag_benchmark_report.py
.\.venv\Scripts\python scripts\rag_answer_benchmark.py --limit 20 --chat-model deepseek-r1:1.5b --num-predict 320 --allow-failures
.\.venv\Scripts\python scripts\rag_answer_benchmark.py --limit 20 --chat-provider openai-compatible --chat-base-url https://api.deepseek.com --chat-model deepseek-v4-flash --chat-thinking enabled --num-predict 640 --allow-failures
.\.venv\Scripts\python scripts\rag_answer_benchmark.py --case-names "refund action,invoice email,router count,teacher no coupon,tone choices,refund paraphrase,hardware paraphrase,invoice paraphrase,content screenshot paraphrase,tone choice paraphrase" --chat-provider openai-compatible --chat-base-url https://api.deepseek.com --chat-model deepseek-v4-flash --chat-thinking enabled --num-predict 1000 --allow-failures
.\.venv\Scripts\python -m pytest backend\tests\test_rag_public_docs_benchmark.py -q
.\.venv\Scripts\python -m pytest backend\tests\test_document_parsing.py backend\tests\test_rag_multiformat_benchmark.py -q
.\.venv\Scripts\python -m pytest backend\tests\test_document_parsing.py backend\tests\test_rag_multiformat_public_docs_benchmark.py -q
.\.venv\Scripts\python scripts\rag_answer_benchmark.py --corpus public-docs --chat-provider openai-compatible --chat-base-url https://api.deepseek.com --chat-model deepseek-v4-flash --chat-thinking enabled --chat-timeout-seconds 150 --num-predict 1000 --allow-failures
.\.venv\Scripts\python scripts\rag_answer_benchmark.py --corpus public-multiformat --chat-provider openai-compatible --chat-base-url https://api.deepseek.com --chat-model deepseek-v4-flash --chat-thinking enabled --chat-timeout-seconds 150 --num-predict 1000 --allow-failures
```

长时间完整回答评测可按原始用例顺序分批运行，避免单次终端超时：

```powershell
.\.venv\Scripts\python scripts\rag_answer_benchmark.py --selection-mode ordered --offset 0 --limit 40 --chat-provider openai-compatible --chat-base-url https://api.deepseek.com --chat-model deepseek-v4-flash --chat-thinking enabled --num-predict 1000 --allow-failures
.\.venv\Scripts\python scripts\rag_answer_benchmark.py --selection-mode ordered --offset 40 --limit 40 --chat-provider openai-compatible --chat-base-url https://api.deepseek.com --chat-model deepseek-v4-flash --chat-thinking enabled --num-predict 1000 --allow-failures
.\.venv\Scripts\python scripts\rag_answer_benchmark.py --selection-mode ordered --offset 80 --limit 40 --chat-provider openai-compatible --chat-base-url https://api.deepseek.com --chat-model deepseek-v4-flash --chat-thinking enabled --num-predict 1000 --allow-failures
.\.venv\Scripts\python scripts\rag_answer_benchmark.py --selection-mode ordered --offset 120 --limit 40 --chat-provider openai-compatible --chat-base-url https://api.deepseek.com --chat-model deepseek-v4-flash --chat-thinking enabled --num-predict 1000 --allow-failures
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

2026-08-02 增加答案生成约束后：

- 约束内容：命中知识库时先核对标题/编号/相关字段；完整保留同一规则、流程、字段组或表格行；保留英文/camelCase 技术词；字段存在但用途未写明时说明边界；明确来源但缺少某字段时回答“未列出该字段”，而不是直接资料不足。
- 上一轮剩余 10 个失败题 targeted 复验：10/10 通过，pass rate 为 100.0%。
- 完整 143 题按 ordered 分批复验：四批分别为 40/40、40/40、40/40、23/23，合计最终回答 143/143，pass rate 为 100.0%；检索门同样 143/143，pass rate 为 100.0%。
- 对外表述建议：在合成评测集上，通过“检索质量 + 答案生成约束”两层优化，把远程 DeepSeek 回答自动评分从 93.0% 提升到 100.0%；边界仍是合成基准，不等同于线上真实用户准确率。

这组数据仍然是合成基准，不是线上真实用户准确率。后续对比远程大模型时应复用同一脚本和同一题集，优先记录：检索门、最终回答正确率、无答案收口率、漏关键事实率和平均耗时。

## 引用、定位与可解释性记录

2026-08-03 补充 M3-A/M3-B/M3-C 引用可解释性切片，目标是把 RAG 从“系统内部偷偷检索”变成用户和开发者都能看见、能复核、能沉淀的证据链。

已完成：

- 后端 `/knowledge/search` 的每条命中会返回 chunk metadata，包括来源格式、文件名、PDF 页码、DOCX 表格行、heading path、chunk type 和分数拆解。
- 关键词/FTS 与 hybrid/vector 路径都保留 metadata，避免开启向量后丢失页码或表格行定位。
- 前端只在本次回答确实注入了 `promptContext` 时，在助手消息下方展示“参考资料”，显示来源、片段编号、检索模式、向量参与状态、分数、位置标签和短摘录。
- 点击参考资料来源会打开“知识”面板并高亮对应资料卡，标出来自聊天引用的片段编号。
- 聊天记录中只保存短摘录级 trace，不重复保存完整 chunk；原始文件仍不保存，知识库删除后后续不再注入。
- M3-B 将 core SQLite schema 提升到 v5，为 `messages` 增加完整 JSON 存储，确保带 `knowledgeTrace` 的助手消息在 SQLite 快照、重启和恢复后仍保留引用证据；旧消息表会非破坏性补列，旧消息仍按基础字段读取。
- M3-C 增加引用片段详情、复制引用证据和单条回答 evidence JSON 导出；导出记录包含上一条用户问题、本条助手回答、检索模式、命中来源、分数拆解、metadata 和短摘录，不包含 API Key 或完整知识库原文。

解决的问题：

- 用户不知道 AI 回答参考了哪份资料，容易把模型生成内容和知识库证据混在一起。
- 开发时难以判断错误来自检索召回、切片、prompt 注入还是聊天模型生成。
- PDF/DOCX 这类资料即使检索正确，也缺少页码、表格行等可定位线索。
- 评测样例此前分散在测试输出和人工记录里，缺少可从真实聊天单条沉淀的证据 JSON。

可记录的工程表述：

- 为本地优先 RAG 增加 source attribution 与 retrieval explainability：将检索命中的 source、chunk、score、mode、PDF page、DOCX table row 等元数据贯穿后端 API、聊天消息和 UI 展示。
- 支持从回答引用一键定位到本地知识库来源，便于人工复核、调试误召回和解释模型答案依据。
- 支持将单条 RAG 回答导出为 evidence JSON，沉淀问题、答案、命中来源、分数与 metadata，便于后续人工复核、回归样例整理和面试展示。
- 配合现有评测脚本，形成“检索门、prompt 注入、最终回答、引用证据、持久化恢复、样例沉淀”六层可观测闭环。

边界：

- 当前定位到 source 级卡片并显示片段编号；片段详情展示的是 trace 中保存的短摘录和 metadata，还没有做知识库原文拉取、全文内高亮、PDF 页预览或 DOCX 原文件打开。
- 引用展示说明的是“本次回答使用了哪些注入片段”，不证明模型回答一定完全正确。
- evidence JSON 是人工复核材料，不是正式评测报告；其中可能包含用户主动提问和回答文本，分享前仍需用户自行检查隐私。
- 如果旧聊天记录没有 `knowledgeTrace` 字段，会继续按普通消息显示。

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
- 当前 UI 可在“知识”面板上传 `.txt/.md/.pdf/.docx` 文本层文件，也保留粘贴纯文本和 Markdown；图表、图片、扫描件和 OCR 仍需要后续策略。

## Evidence 到 Benchmark Case 的沉淀流程

RAG-M4-A 增加 `scripts/rag_evidence_case_tool.py`，把 UI 导出的单条回答 evidence JSON 转成可人工复核的 benchmark case draft。这个工具只读取命令行显式传入的 JSON/JSONL，不扫描 Electron `userData`、真实 SQLite 或用户目录，也不会上传任何内容。

推荐本地流程：

```powershell
.\.venv\Scripts\python scripts\rag_evidence_case_tool.py draft --input .\path\to\suoyi-rag-evidence.json --output .suoyi-rag-cases\drafts\case.json
.\.venv\Scripts\python scripts\rag_evidence_case_tool.py validate --input .suoyi-rag-cases\drafts\case.json
.\.venv\Scripts\python scripts\rag_evidence_case_tool.py to-jsonl --input .suoyi-rag-cases\reviewed --output .suoyi-rag-cases\reviewed-cases.jsonl
```

草稿 case 使用 `suoyi-rag-benchmark-case-v1`。工具会自动填入 query、检索模式、top source、短摘录、metadata 和隐私初始状态；`requiredFacts`、`forbiddenFacts`、`requiredSourceTitles` 等期望字段必须由人工补全或确认。默认草稿为 `status=draft`、`safeToCommit=false`、`containsUserPrivateText=true`，不能计入正式通过率，也不应直接提交到仓库。

已人工复核的 case 可以标记为 `reviewed` 或 `active`，并用现有回答评测入口运行：

```powershell
.\.venv\Scripts\python scripts\rag_evidence_case_tool.py validate --input backend\tests\fixtures\rag_evidence_cases\synthetic_cases.jsonl --require-runnable
.\.venv\Scripts\python scripts\rag_answer_benchmark.py --corpus public-multiformat --case-file backend\tests\fixtures\rag_evidence_cases\synthetic_cases.jsonl --allow-failures
```

`--case-file` 只接受 `reviewed/active` 且 expected 字段完整的 case，并要求 case 的 `corpus.id` 与 `--corpus` 一致。回答评测仍会按所选 corpus 重新 seed 临时 SQLite，再执行检索、可选 embedding reindex 和聊天模型评分；如果本地 Ollama 或远程聊天模型不可用，这一步可能失败，不影响 case 转换工具本身。

安全边界：

- evidence JSON 和 draft case 可能包含用户问题、助手回答和短摘录，默认按本地私有材料处理。
- 工具发现疑似 `sk-`、`Bearer ...`、`GH_TOKEN`、`github_pat_`、Cookie、access token 或 API Key 字段值时会拒绝处理，并且错误信息不回显密钥原文。
- 仓库中只提交合成或公开摘要 fixture；真实私有 case 建议放在 `.suoyi-rag-cases/`，该目录已加入 `.gitignore`。
- evidence 转 case 能让样例持续沉淀和复跑，但它不自动判断答案正确，也不证明线上真实准确率。

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

## 公开官方文档摘要基准

为了避免只在自造业务资料上报喜，新增 public-docs 基准：资料来自公开官方文档，但仓库中只保存自写短摘要和来源 URL 常量，不复制长网页正文，不包含用户隐私或真实密钥。

资料来源覆盖：

- React useEffect：https://react.dev/reference/react/useEffect
- Vite 环境变量：https://vite.dev/guide/env-and-mode
- Electron 安全：https://www.electronjs.org/docs/latest/tutorial/security
- FastAPI TestClient：https://fastapi.tiangolo.com/tutorial/testing/
- SQLite FTS5：https://www.sqlite.org/fts5.html
- Ollama API：https://docs.ollama.com/api
- DeepSeek API：https://api-docs.deepseek.com/
- MDN Fetch API：https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch
- GitHub Actions GITHUB_TOKEN：https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication
- Python venv：https://docs.python.org/3/library/venv.html
- TypeScript TSConfig：https://www.typescriptlang.org/tsconfig/
- electron-builder：https://www.electron.build/

2026-08-02 public-docs 自动化检索基准：

- 资料规模：12 份官方文档摘要 + 18 份相似干扰资料，共 30 份文档。
- 切片规模：使用本地 Ollama `bge-m3` 重建向量索引后为 71 个 active chunk。
- 问题规模：62 题，其中 50 题为 lexical/FTS、12 题为 hybrid/Ollama embedding 口语改写。
- `backend/tests/test_rag_public_docs_benchmark.py`：4 passed，覆盖 top1 source、promptContext 必含/禁含、泛字段不注入、表格行切片、删除后不召回。
- 旧 RAG 回归：`test_rag_quality.py`、`test_rag_realistic_benchmark.py`、`test_rag_h2_quality.py` 合计 12 passed。

本轮 public-docs 发现并修复的真实问题：

- 技术泛字段不够泛：用户只问 “Base URL 是什么？”、“端点是什么？”、“权限是什么？” 时，旧逻辑可能把相似资料注入。修复后这些问题需要指定来源；如果用户问 “DeepSeek API 的 Base URL 是什么？” 仍可命中目标资料。
- 来源标题匹配过窄：用户说 “Vite/FastAPI/DeepSeek” 时，不一定会完整说出“官方摘要”。修复后会识别标题里的唯一别名或多个标题词组合，减少跨 source 混入。
- URL 正文污染切片：把“来源 URL”直接放进知识正文会产生只有链接的弱信息 chunk。public-docs 改为在代码常量中保留来源 URL，知识正文只放摘要事实。
- 真实向量语义过宽：`bge-m3` 曾把“浏览器请求 500 是否进 catch”拉向“浏览器存储”干扰资料。修复后 HTTP/Fetch/catch/status 类查询的向量候选必须带请求语义锚点，避免只靠“浏览器”这种大词进 prompt。

2026-08-02 public-docs 端到端回答评测：

- embedding：本地 Ollama `bge-m3`，不向远程发送资料片段。
- chat：远程 OpenAI-compatible `deepseek-v4-flash`，thinking enabled；Key 只从本机环境变量读取，不写入文档、日志或仓库。
- 探索性全量：60/62，失败包括 1 次网络超时和 1 次远程模型偶发“资料不足”；针对失败题复跑 2/2 通过。
- HTTP/Fetch 锚点修复前全量复验：61/62，剩余失败为真实 retrieval 误召回。
- HTTP/Fetch 锚点修复后最终全量复验：检索门 62/62，最终回答 62/62，pass rate 为 100.0%。
- 表述边界：这是公开官方文档摘要基准上的结果，比纯合成资料更接近真实资料形态，但仍不是线上真实用户准确率；未来加入 PDF/图片/图表解析后需要重新建立对应基准。

## 多格式文本层导入基准

RAG-M2-A 新增后端文件解析层，目标是先覆盖真实资料里最稳定的文本层，而不是一次性承诺所有文档形态。自动化测试使用 pytest 临时目录生成短小的 PDF/DOCX/TXT/Markdown fixture，不使用用户私人文件，不复制长网页正文，也不调用真实 embedding 或聊天模型服务。

当前覆盖：

- `.txt/.md`：UTF-8 文本解析，文件过大、空文件、编码不支持时返回明确错误。
- PDF：只解析已有文本层，按页生成 `## 第 N 页` heading，并把页码写入 chunk metadata；空白/扫描件 PDF 返回“当前暂不支持自动 OCR”。
- DOCX：提取标题、段落、列表和表格行；表格一行会保留为同一个 fact block，避免把编号、预算、负责人、截止日期切散。
- 检索：多格式导入后复用现有结构化 chunk、FTS5/BM25、mock hybrid、软删除和 prompt 注入门槛。指定来源字段题不混入其他资料，泛字段和无关问题不注入，删除后 FTS/hybrid 都不召回。

运行命令：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_document_parsing.py -q
.\.venv\Scripts\python -m pytest backend\tests\test_rag_multiformat_benchmark.py -q
```

边界：

- 当前不做 OCR、图片/图表视觉理解、PDF 扫描件解析、旧版 `.doc`、联网抓取或云解析。
- 后端默认不保存原始上传文件，只保存解析后的文本、表格行和页码/章节等 metadata。
- M2-B 已把文件上传入口接入“知识”面板；上传仍只走文本层解析，不保存原始文件副本。

## 多格式公开资料基准

RAG-M2-C 把 public-docs 的思路迁移到真实文件入口：资料仍来自公开官方文档，但仓库中只保存自写短摘要和来源 URL 常量；导入路径改为 `/knowledge/import/file` multipart，覆盖 Markdown、TXT、文本层 PDF 和 DOCX，不使用用户私人资料，不复制长网页正文，也不调用真实 embedding 或聊天模型服务。

2026-08-03 M2-C 自动化检索基准：

- 资料规模：10 份公开官方文档摘要 + 14 份相似干扰资料，共 24 份文件。
- 文件格式：Markdown、TXT、文本层 PDF、DOCX；PDF/DOCX fixture 在测试中本地生成。
- 问题规模：59 题，其中 47 题为 lexical/FTS、12 题为 mock hybrid embedding 口语改写。
- 验证范围：top1 source、promptContext 必含/禁含、泛字段不注入、无关问题不注入、DOCX 表格行 metadata、PDF 页码 metadata、删除后不召回。
- `backend/tests/test_document_parsing.py` + `backend/tests/test_rag_multiformat_public_docs_benchmark.py`：11 passed，1 个 Starlette/httpx deprecation warning。

本轮 M2-C 发现并修复的真实问题：

- PDF 文件信息污染检索：解析器之前把“来源格式/文件名/页数”等文件信息写进可检索正文，可能排在真实答案片段前面。修复后 PDF 正文只保留文档标题和文本页内容，文件名/页数继续放在 metadata。
- DOCX 表格邻近字段容易被拆散：DOCX block 拼接改得更紧凑，表格行里的相邻字段更稳定地保持在同一结构块里。
- 表格字段识别不够通用：新增“项目/建议/原因”事实标签，让常见说明型表格行可识别为 `fact_block`，避免只作为普通段落处理。

表述边界：M2-C 证明的是多格式文本层文件在公开摘要基准上的“检索与 prompt 注入”稳定性，不是图片、图表、扫描件 OCR，也不是线上真实用户最终回答准确率。

## 多格式公开资料端到端回答评测

RAG-M2-D 在 M2-C 的同一批多格式公开资料上继续评测最终回答正确率：先通过本地 Ollama `bge-m3` 建索引与检索，再把 promptContext 交给远程 OpenAI-compatible `deepseek-v4-flash` 生成答案。API Key 只从本机环境变量读取，不写入文档、日志、SQLite、测试 fixture 或提交记录。

2026-08-03 M2-D 端到端结果：

- 语料：10 份公开官方文档摘要 + 14 份相似干扰资料，共 24 份文件。
- 格式：Markdown、TXT、文本层 PDF、DOCX。
- 切片/索引：68 个 active chunk，本地 Ollama `bge-m3` embedding health 通过并完成 reindex。
- 问题：59 题，其中 47 题 lexical/FTS，12 题 hybrid/Ollama embedding 口语改写；包含 53 个应注入题、4 个澄清题、2 个无答案题。
- 检索门：59/59 通过，pass rate 为 100.0%。
- 最终回答：59/59 通过，pass rate 为 100.0%；lexical/FTS 为 47/47，hybrid 为 12/12。

本轮 M2-D 发现的评测口径问题：

- 初始严格评分为 58/59，唯一失败是用户问题已经包含 `OpenAI compatible`，模型回答了真正被问的 `/chat/completions`，但没有重复该上下文词。评分器已修正为：如果缺失词已经出现在用户问题中，且模型答出了其他关键事实，则不视为错误。修正后同一题单独复验通过，全量复验为 59/59。

对外表述建议：可以说“在 24 份公开官方摘要多格式文件、59 题端到端基准上，本地 bge-m3 hybrid 检索门 100.0%，远程 DeepSeek 最终回答自动评分 100.0%”。必须同时说明：这是公开摘要和文本层文件基准，不等同于用户真实私有资料、扫描件/OCR/图片图表或线上全场景准确率。
