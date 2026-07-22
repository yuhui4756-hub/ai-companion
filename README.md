# 所依

一个中文 BYOK（Bring Your Own Key，自带 API Key）AI 恋爱伴侣应用。当前以“单聊天页”为主体验：左侧只保留伴侣列表、新建和更多入口，中间专注聊天，顶部按钮打开伴侣、记忆、风格、设置和用户须知弹窗；旧朋友、理性支持、日常陪伴、角色陪伴类型默认收进更多/兼容入口。

## 下载最新版

Windows 用户可以直接下载安装包：

- 下载地址：[suoyi-setup-0.1.3.exe](https://github.com/yuhui4756-hub/ai-companion/releases/download/v0.1.3/suoyi-setup-0.1.3.exe)
- Release 页面：[所依 v0.1.3](https://github.com/yuhui4756-hub/ai-companion/releases/tag/v0.1.3)

`v0.1.3` 已公开发布到 GitHub Release。本版包含 RAG-Q1/H1 检索升级和 packaged sidecar schema smoke 增强；旧 `v0.1.2` Release 保留为手动回退下载点。

当前安装包还没有配置代码签名，Windows 可能提示“未知发布者”。这是当前版本的已知边界，不需要关闭系统安全防护。

## 已实现功能

- 恋爱陪伴主创建流程：第一次打开且还没有用户创建过伴侣时，优先创建男友/女友方向的恋爱伴侣；也可以跳过并使用默认女友。创建完成后不会自动插入伴侣开场消息，聊天从用户开口开始。
- 单聊天页信息架构：不再常驻展示伴侣、记忆、风格、设置等后台式页面；这些能力都通过顶部短按钮打开弹窗或详情面板。
- 恋爱模板 registry：女友方向和男友方向各 6 个主模板，主模板决定长期底色；女友方向优先展示温柔可爱、傲娇、御姐，男友方向优先展示温柔男友、成熟哥哥、霸总型。
- 融合气质：可选择 1-3 个融合特质，让伴侣在安慰、调侃、撒娇、轻微吃醋、认真陪伴等场景里有变化，但不变成多重人格。
- 自定义恋爱人设 / system prompt：可本地编辑完整人设；明显包含 API Key、身份证/银行卡、冒充真人、伪造线下承诺、露骨成人、违法危险或强控制依赖的内容会被本地校验温和提示并阻止保存。
- 用户须知集中入口：隐私、本地保存、API Key、AI 伴侣透明说明和自定义人设边界集中在“用户须知”，不在聊天和创建流程里反复打断。
- 旧伴侣兼容：朋友陪伴、日常陪伴、理性支持、角色扮演等旧类型仍可访问、聊天、编辑和导出；默认不出现在聊天主列表，可从更多/兼容入口恢复显示。
- 自定义伴侣：名字、关系类型、当前提示词/核心人设、回应节奏和性格/特质组合；新建伴侣先在伴侣面板内生成草稿，取消不落盘，保存后才加入列表。
- BYOK 配置：`providerName`、`baseURL`、`model`、`apiKey`，并提供 DeepSeek / OpenAI 兼容预设；预设不会填写 API Key。
- OpenAI Chat Completions 兼容接口调用，桌面版优先经本机 Electron 主进程代理转发，Web 调试版无桌面代理时保留浏览器直连 fallback；当前模型请求为非流式，前端会把多段回复拆成连续消息逐段显示。
- 长期记忆本地管理：区分全局记忆和当前伴侣专属记忆，支持手动新增、查看、编辑、删除。
- 聊天时会轻量自动识别明确偏好、称呼、禁忌、目标纠正和情绪模式，并沉淀为可管理的本地记忆；敏感信息和不健康依赖表达不会作为长期记忆保存。
- 聊天时会按相关性把全局记忆、当前伴侣专属记忆和风格摘要注入提示词；删除、失效或被替换的记忆不会注入。
- 本地 SQLite 后端：Python/FastAPI 后端保存知识库资料，并可把伴侣、聊天、长期记忆、风格摘要和去 Key 的模型配置从旧 `localStorage` 快照迁入 SQLite；旧 `localStorage` 保留作回退。
- 本地知识库：可在顶部“知识”入口手动导入文本或 Markdown；启动 Python 本地后端后，资料会写入本机 SQLite、按 Markdown 标题/列表/表格/问答/事实字段结构切片，并通过本地 FTS5/BM25 或关键词 fallback 检索；相关且置信足够时把命中片段标记为“用户导入资料”后注入，泛字段或低置信问题不强行注入；删除资料后不再注入。远程向量检索默认关闭，用户单独配置 embedding 服务商和 Key 并重建索引后，才会参与 hybrid retrieval。
- 风格参考摘要：可粘贴有权使用的参考文本，在本地生成/编辑摘要字段，并绑定到某个虚构 AI 伴侣；不会默认发送给第三方模型。
- 清楚的错误提示：缺少配置、认证失败、网络失败、模型错误、响应格式异常。
- 设置弹窗可清除本地 API Key、当前聊天、长期记忆、风格摘要，并导出不含 API Key、原始聊天记录和知识库原文的配置/记忆 JSON。
- 预留 `channel-adapter`，当前提供 OneBot 本地连接实验骨架和 mock 验证；这不是腾讯官方机器人通道，不内置 NapCat，也不处理 QQ 密码、Cookie 或扫码凭证。

## Windows 桌面版：所依

v0.1.3 已发布 Windows 桌面安装包。用户可见应用名统一为“所依”，桌面窗口会隐藏系统默认 `File / Edit / View / Window / Help` 菜单栏，改用应用内自定义标题栏和最小化、最大化/还原、关闭按钮，并接入正式应用图标。

桌面版更新源使用公开 GitHub Releases。客户端不内置 GitHub token；发布 token 只能用于发布端环境变量或 CI Secret，不能写入客户端或配置文件。已安装 `0.1.2` 的桌面端在检查更新时可发现 `0.1.3`，并由用户确认后下载和重启安装；真实覆盖式自动更新验收仍需单独按用户数据保护方案执行。

网页版和桌面版的数据空间不同。数据迁移需要通过“设置 -> 从网页版导入备份”显式完成，API Key 不在备份里，需要在桌面版重新填写。

从源码构建桌面版：

```bash
npm run backend:build-sidecar
npm run desktop:dir
npm run desktop:dist
```

`desktop:dir` 和 `desktop:dist` 会先用 PyInstaller 构建本地 Python sidecar，并把 `backend/dist/suoyi-backend/` 内置到桌面候选资产的 `resources/python-backend/` 下。`desktop:dist` 仍固定 `--publish never`，避免构建时误上传；公开发布由总控核验后手动上传到 GitHub Release。

## 从源码本地启动

如果只是使用所依，优先下载上面的 Windows 安装包。下面是开发者或调试时从源码启动 Web 版的方式。

第一次使用前，需要先安装 Node.js LTS 版本：

```text
https://nodejs.org/
```

安装好以后，在项目文件夹里双击：

```text
启动AI伴侣.bat
```

脚本会做这些事：

- 检查电脑有没有 Node.js / npm。
- 第一次缺少 `node_modules` 时自动执行 `npm install`。
- 用固定地址启动并打开：

```text
http://127.0.0.1:5173/
```

停止运行：回到启动时弹出的命令窗口，按 `Ctrl + C`，再按提示输入 `Y`。

如果提示 5173 端口已经被占用，通常说明已经有一个所依 Web 预览窗口或服务在运行。可以直接打开 `http://127.0.0.1:5173/` 继续用，或者关闭旧命令窗口后再双击启动。

## 预览构建版

想从源码检查 Web 构建后的效果，可以双击：

```text
构建并预览AI伴侣.bat
```

它会先执行构建，再用同一个固定地址 `http://127.0.0.1:5173/` 预览，避免 Vite 默认预览端口造成本地数据看起来“消失”。

## 命令行启动

先确认电脑已经安装 Node.js。然后在项目目录运行：

```bash
npm install
npm run dev
```

看到类似下面的地址后，用浏览器打开：

```text
http://127.0.0.1:5173/
```

停止运行：回到运行 `npm run dev` 的命令行窗口，按 `Ctrl + C`。

## Python 本地后端（SQLite / 知识库）

Web 调试版可以另开一个本机 Python 后端窗口。它处理本地 SQLite、核心数据快照迁移、知识库切片和检索，不接收模型 API Key。

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8765
```

检查后端状态：

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
Invoke-RestMethod http://127.0.0.1:8765/core/status
```

桌面开发态会尝试由 Electron 自动托管 `.venv` 里的 Python 后端：默认端口 `8765`，占用时尝试 `8766-8780`。桌面打包态会启动 `resources/python-backend/suoyi-backend.exe`。托管时 SQLite 文件会放到 Electron `userData` 下的 `backend/suoyi.sqlite`。`v0.1.3` 公开安装包已内置 schema v4 sidecar，用于远程向量检索和增强核验脚本。

## 怎么使用

1. 打开网页后，先按恋爱创建流程选择男友/女友方向、主模板和融合气质；不确定也可以先跳过，用默认女友开始。
2. 需要细调时，点顶部“伴侣”打开管理面板，编辑“恋爱人设 / system prompt”。这段只保存在当前浏览器本地，保存前会做本地边界检查。
3. 点顶部“设置”，可以先点 DeepSeek 或 OpenAI 兼容预设，再填写你的 OpenAI 兼容接口：
   - `baseURL` 示例：`https://api.openai.com/v1` 或 `https://api.deepseek.com`
   - `model` 示例：填写你的服务商支持的模型名，预设值可以手动修改
   - `apiKey`：填写你自己的 Key，只保存在当前浏览器本地，不要发给测试线程或写进文档
4. 关闭弹窗回到聊天，直接开始对话。
5. 点顶部“伴侣”可以继续编辑当前恋爱伴侣，也可以从更多/兼容入口访问旧类型伴侣，或把旧伴侣恢复显示到主列表。
6. 点顶部“记忆”查看、编辑、新增或删除全局/专属长期记忆。
7. 点顶部“知识”可以手动导入你授权使用的文本或 Markdown；相关提问时才会注入命中片段，删除后不再注入。
8. 点顶部“风格”可以导入或添加风格参考摘要，并绑定到当前伴侣。

## 隐私说明

当前应用没有云端后端服务器。API Key 默认仍保存在当前浏览器或桌面应用本地的 `localStorage`；本地 Python 后端可用时，聊天记录、长期记忆、伴侣配置、风格摘要和去 Key 的模型配置会复制保存到本机 SQLite，旧 `localStorage` 不会自动清空。项目不内置、不提交任何真实 Key。

聊天时，桌面版会优先经本机 Electron 主进程代理转发到你配置的模型服务商；Web 调试版没有桌面代理时，仍可能由浏览器直接请求你填写的 OpenAI 兼容接口。首次打开页面会显示用户须知弹窗，确认状态也只保存在当前环境本地；后续可从顶部“须知”按钮重新打开。

知识库资料默认只保存在本地。聊天时，前端会把最新用户输入发给本机 Python 后端做本地检索；只有命中的相关片段会随当前模型请求发给你配置的模型服务商。删除资料会软删除对应来源和切片，后续不再注入。

当前 RAG 默认使用本地 FTS5/BM25 与关键词规则基线。远程向量检索是单独开关：只有用户明确开启、填写 embedding Key 并构建索引时，active 资料切片才会发给用户配置的 embedding 服务商；聊天检索时也只有在向量索引 ready 且问题有明确检索线索时，才会把本次 query 发给该 embedding 服务商。Embedding Key 与聊天模型 Key 分开，默认只保存在当前环境本地 `localStorage`，不写入 SQLite、导出 JSON、日志或安装包。向量本身属于知识库资料的派生隐私数据，也不默认导出。

导出配置/记忆 JSON 时会移除 API Key，且默认不导出原始聊天记录和知识库原文。导出文件仍可能包含你的偏好、长期记忆和伴侣设定，请妥善保存。

风格参考只用于描述表达风格，不能复刻、复活或冒充任何真实个人。P0 版本的风格摘要流程在本地完成，不会把导入文本默认发送给模型服务商。

设置页里的 OneBot 本地连接只是实验功能：所依只保存本机 OneBot 连接地址和用户填写的 access token，不保存 QQ 密码、Cookie、扫码凭证，也不会把模型 API Key 发送给 OneBot/NapCat。群聊默认不主动响应，后续实验也应只在 @ 或唤醒词触发时回复。

注意：Web 调试版在没有桌面代理时会直接请求你填写的接口。如果某些服务商不允许网页跨域访问，可能会出现网络失败；桌面版优先使用本机 Electron 代理来减少这类跨域问题。

## 本地数据在哪里

桌面版和网页版的数据空间不同：

- 桌面版数据保存在 Electron 应用自己的本地数据目录里，升级同一个应用不会主动清空这些数据。
- 网页版/源码调试版数据保存在“当前浏览器 + 当前访问地址”的 `localStorage` 里。
- Python 后端开发默认保存在 `backend/data/suoyi-dev.sqlite`，也可以用 `SUOYI_BACKEND_DB_PATH` 指定 SQLite 文件；Electron 开发态和打包态托管时使用应用 `userData/backend/suoyi.sqlite`；`backend/data/`、`backend/dist/`、`.sqlite/.db` 文件不会提交。

为了让 Web 调试数据连续，本地启动统一使用：

```text
http://127.0.0.1:5173/
```

请尽量不要混用 `localhost`、其他端口或其他浏览器。浏览器会把这些当成不同空间；如果换了地址、端口、浏览器，或者清理了浏览器数据，就可能看起来像伴侣、记忆或 API Key 不见了。

如果要换电脑、换浏览器，或从网页版迁移到桌面版，建议先在“设置”里导出配置/记忆作为备份，再在新环境中导入。导出文件不包含 API Key，也不默认包含原始聊天记录和知识库原文。

## 当前边界

- v0.1.3 已提供 Windows 桌面安装包和公开 GitHub Release；v0.1.2 Release 保留为手动回退下载点。
- 当前没有后端账号系统，也没有云同步；数据默认保存在本地。核心数据 SQLite 迁移是本机复制导入，失败时继续使用 `localStorage`。
- 当前公开安装包已内置 Python sidecar、本地 SQLite 知识库、核心数据迁移、RAG-Q1 结构化切片/FTS5-BM25、RAG-H1 远程 embedding 隐私门控与 hybrid retrieval，并通过发布候选 sidecar schema smoke 增强降低旧后端误打包风险。后续仍需继续完善细粒度 CRUD、恢复/清理 UI、SQLite 加密或 OS 安全存储。
- 远程向量检索目前是轻量 hybrid retrieval：SQLite 保存 JSON 向量，Python 本地计算余弦相似度并与 BM25/关键词结果融合；没有引入远程向量库、云同步或重型本地向量数据库。
- QQ 近期只做 OneBot/NapCat 本地实验骨架；QQ 官方机器人保留为长期合规备选，微信继续暂缓。
- Release 产物由构建命令生成，不提交进源码仓库。

## 常用命令

```bash
npm run dev
npm run build
npm run preview
npm run backend:build-sidecar
npm run desktop:dir
npm run desktop:dist
```

