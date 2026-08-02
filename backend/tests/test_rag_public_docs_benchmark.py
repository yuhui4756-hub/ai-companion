from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.tests.test_rag_realistic_benchmark import BenchmarkCase, evaluate_case


PUBLIC_SOURCE_URLS = {
    "React useEffect 官方摘要": "https://react.dev/reference/react/useEffect",
    "Vite 环境变量官方摘要": "https://vite.dev/guide/env-and-mode",
    "Electron 安全配置官方摘要": "https://www.electronjs.org/docs/latest/tutorial/security",
    "FastAPI TestClient 官方摘要": "https://fastapi.tiangolo.com/tutorial/testing/",
    "SQLite FTS5 BM25 官方摘要": "https://www.sqlite.org/fts5.html",
    "Ollama Embeddings 官方摘要": "https://docs.ollama.com/api",
    "DeepSeek API 官方摘要": "https://api-docs.deepseek.com/",
    "MDN Fetch API 官方摘要": "https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch",
    "GitHub Actions 自动令牌官方摘要": "https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication",
    "Python venv 官方摘要": "https://docs.python.org/3/library/venv.html",
    "TypeScript TSConfig 官方摘要": "https://www.typescriptlang.org/tsconfig/",
    "Electron Builder 发布摘要": "https://www.electron.build/",
}


def public_runtime_config() -> dict:
    return {
        "providerName": "mock",
        "baseURL": "http://127.0.0.1:8765/mock",
        "model": "mock-embedding-public-docs",
        "dimensions": 64,
        "batchSize": 4,
        "timeoutMs": 3000,
        "enabled": True,
        "apiKey": "mock-local-key",
    }


PUBLIC_DOCUMENTS = [
    {
        "title": "React useEffect 官方摘要",
        "sourceType": "markdown",
        "content": """
# React useEffect 官方摘要

## 副作用生命周期
术语：useEffect 是 React Hook，用来让组件和外部系统同步。
setup 函数可以返回 cleanup 函数。
执行顺序：依赖变化后，React 会先用旧值运行 cleanup，再用新值运行 setup。
卸载规则：组件从页面移除后，React 会最后运行 cleanup。
依赖比较：dependencies 必须写成内联数组，React 使用 Object.is 比较每一项。
边界：如果没有外部系统需要同步，通常不需要 Effect。
""".strip(),
    },
    {
        "title": "Vite 环境变量官方摘要",
        "sourceType": "markdown",
        "content": """
# Vite 环境变量官方摘要

## 客户端变量
访问方式：在源码中通过 import.meta.env 读取环境变量。
暴露规则：只有以 VITE_ 开头的变量会暴露给客户端代码。
类型规则：环境变量值会以字符串形式暴露，业务代码需要自行转换布尔值或数字。
重启规则：修改 .env 文件后需要重启开发服务器。
内置字段：import.meta.env.MODE、DEV、PROD、SSR 和 BASE_URL 是 Vite 提供的内置字段。
""".strip(),
    },
    {
        "title": "Electron 安全配置官方摘要",
        "sourceType": "markdown",
        "content": """
# Electron 安全配置官方摘要

## BrowserWindow 边界
节点集成：加载远程内容的窗口不要启用 nodeIntegration。
上下文隔离：contextIsolation 应保持开启，让 preload 与网页运行在不同上下文。
沙箱：sandbox 可以减少渲染进程可用的特权能力。
Web 安全：不要关闭 webSecurity。
Preload 暴露：只通过 contextBridge 暴露最小白名单 API，不要把 ipcRenderer 或 Node fs/path/process/shell 直接暴露给页面。
IPC 边界：主进程需要校验消息来源和参数。
""".strip(),
    },
    {
        "title": "FastAPI TestClient 官方摘要",
        "sourceType": "markdown",
        "content": """
# FastAPI TestClient 官方摘要

## 测试方式
导入方式：从 fastapi.testclient 导入 TestClient。
创建方式：用 TestClient(app) 包装 FastAPI 应用。
调用方式：测试代码可以使用 client.get、client.post 等方法调用路径。
断言方式：常见断言包括 status_code 和 response.json()。
运行边界：TestClient 允许在测试进程内调用应用，不需要单独启动 uvicorn 服务。
""".strip(),
    },
    {
        "title": "SQLite FTS5 BM25 官方摘要",
        "sourceType": "markdown",
        "content": """
# SQLite FTS5 BM25 官方摘要

## 全文检索
创建方式：可以用 CREATE VIRTUAL TABLE docs USING fts5(title, body) 创建 FTS5 虚表。
查询方式：全文检索使用 MATCH 表达式，例如 docs MATCH 'sqlite'。
排序函数：bm25(fts_table) 可以作为相关性排序信号。
排序方向：FTS5 的 bm25 分数越小表示匹配越好，常见写法是 ORDER BY bm25(fts_table)。
索引边界：FTS 虚表需要和真实业务表保持同步，删除资料后不能让旧 chunk 继续参与 MATCH。

## 示例表
| 项目 | 写法 | 用途 |
| --- | --- | --- |
| 虚表 | CREATE VIRTUAL TABLE docs USING fts5(title, body) | 建立全文索引 |
| 查询 | docs MATCH 'sqlite' | 过滤匹配文档 |
| 排序 | ORDER BY bm25(docs) | 让更相关的结果排在前面 |
""".strip(),
    },
    {
        "title": "Ollama Embeddings 官方摘要",
        "sourceType": "markdown",
        "content": """
# Ollama Embeddings 官方摘要

## Embed API
本地地址：Ollama 默认在 http://127.0.0.1:11434 提供本机服务。
端点：/api/embed 用于从输入文本生成 embedding 向量。
请求字段：请求体包含 model 和 input。
输入形态：input 可以是一段文本，也可以是多段文本列表。
响应字段：响应里包含 embeddings 数组。
安全边界：本地 Ollama embedding 不需要把资料片段发送给远程 embedding 服务商。
""".strip(),
    },
    {
        "title": "DeepSeek API 官方摘要",
        "sourceType": "markdown",
        "content": """
# DeepSeek API 官方摘要

## OpenAI 兼容接口
Base URL：https://api.deepseek.com
兼容格式：DeepSeek API 使用 OpenAI 兼容的请求格式。
聊天端点：Chat Completions 使用 /chat/completions 路径。
模型字段：请求体通过 model 指定模型。
认证边界：Authorization header 携带 Bearer API Key，应用日志和文档不能记录完整 Key。
RAG 边界：模型请求可能接收用户问题、聊天上下文和命中的知识片段，所以资料注入要经过隐私门控。
""".strip(),
    },
    {
        "title": "MDN Fetch API 官方摘要",
        "sourceType": "markdown",
        "content": """
# MDN Fetch API 官方摘要

## 请求与响应
调用方式：fetch() 返回一个 Promise，成功时解析为 Response。
HTTP 边界：404 或 500 这类 HTTP 错误状态不会自动让 Promise reject。
错误判断：业务代码应检查 response.ok 或 response.status。
读取方式：Response 的 json()、text() 等方法会读取响应体。
请求体：发送 JSON 时通常设置 Content-Type: application/json，并把对象 JSON.stringify。
""".strip(),
    },
    {
        "title": "GitHub Actions 自动令牌官方摘要",
        "sourceType": "markdown",
        "content": """
# GitHub Actions 自动令牌官方摘要

## 权限控制
自动令牌：GitHub 会为 workflow job 提供 GITHUB_TOKEN。
权限声明：可以用 permissions 字段限制令牌权限。
最小权限：应该只给工作流需要的权限。
发布边界：上传 Release 资产通常需要 contents: write 权限。
安全边界：不要把令牌打印到日志，不要把令牌写进仓库文件。
""".strip(),
    },
    {
        "title": "Python venv 官方摘要",
        "sourceType": "markdown",
        "content": """
# Python venv 官方摘要

## 虚拟环境
创建方式：python -m venv .venv 会创建一个独立虚拟环境目录。
用途：虚拟环境拥有自己的 Python 可执行文件和 site-packages。
激活方式：Windows PowerShell 常见激活脚本是 .venv\\Scripts\\Activate.ps1。
依赖边界：项目依赖应安装进虚拟环境，避免污染系统 Python。
删除边界：删除虚拟环境目录不会删除项目源码。
""".strip(),
    },
    {
        "title": "TypeScript TSConfig 官方摘要",
        "sourceType": "markdown",
        "content": """
# TypeScript TSConfig 官方摘要

## 编译配置
配置文件：tsconfig.json 描述 TypeScript 项目的根文件和编译选项。
noEmit：开启 noEmit 后，编译器只做类型检查，不输出 JavaScript 文件。
strict：strict 会启用一组更严格的类型检查规则。
include：include 用来声明参与编译的文件匹配范围。
边界：tsconfig 是源码检查配置，不应该包含用户密钥或运行时数据。
""".strip(),
    },
    {
        "title": "Electron Builder 发布摘要",
        "sourceType": "markdown",
        "content": """
# Electron Builder 发布摘要

## Windows 候选包
构建目标：electron-builder 可以为 Windows 生成 NSIS 安装包和 win-unpacked 目录。
发布控制：publish never 表示构建本地候选资产但不上传发布。
更新文件：latest.yml 用于自动更新元数据，通常包含版本、文件名、sha512 和 size。
资源边界：打包资源不应混入本地 SQLite 数据库、.env 文件、虚拟环境或测试 fixture。
""".strip(),
    },
]


def build_public_distractor_documents(count: int = 18) -> list[dict[str, str]]:
    topics = [
        ("浏览器存储摘要", "localStorage 存储字符串键值，清理站点数据会影响保存内容。"),
        ("CSS Grid 摘要", "grid-template-columns 描述网格列轨道，gap 设置行列间距。"),
        ("Node 事件摘要", "EventEmitter 使用 on 注册监听，emit 触发事件。"),
        ("pytest fixture 摘要", "fixture 可以为测试准备输入数据和清理逻辑。"),
        ("Pydantic 模型摘要", "BaseModel 用字段类型定义输入输出结构。"),
        ("PowerShell 脚本摘要", "ExecutionPolicy 影响脚本运行策略，-NoProfile 可减少环境干扰。"),
    ]
    documents: list[dict[str, str]] = []
    for index in range(1, count + 1):
        topic, description = topics[(index - 1) % len(topics)]
        documents.append(
            {
                "title": f"公开文档干扰资料 {index:02d} {topic}",
                "sourceType": "markdown",
                "content": f"""
# 公开文档干扰资料 {index:02d} {topic}

## 摘要
编号：PUBLIC-DISTRACTOR-{index:02d}
说明：{description}
边界：这份资料只用于扩大公开文档知识库规模，不应替代目标官方摘要。
""".strip(),
            }
        )
    return documents


PUBLIC_DISTRACTOR_DOCUMENTS = build_public_distractor_documents()
PUBLIC_BENCHMARK_DOCUMENTS = [*PUBLIC_DOCUMENTS, *PUBLIC_DISTRACTOR_DOCUMENTS]


PUBLIC_LEXICAL_CASES = [
    BenchmarkCase("react cleanup before setup", "React useEffect 依赖变化时 cleanup 和 setup 的顺序是什么？", "React useEffect 官方摘要", ("先用旧值运行 cleanup", "再用新值运行 setup"), ("VITE_",)),
    BenchmarkCase("react unmount cleanup", "React useEffect 组件卸载后会运行什么？", "React useEffect 官方摘要", ("最后运行 cleanup",), ("TestClient",)),
    BenchmarkCase("react dependency compare", "React useEffect 依赖项用什么比较？", "React useEffect 官方摘要", ("Object.is",), ("response.ok",)),
    BenchmarkCase("react external boundary", "React useEffect 没有外部系统同步时还需要吗？", "React useEffect 官方摘要", ("通常不需要 Effect",), ("GITHUB_TOKEN",)),
    BenchmarkCase("vite client prefix", "Vite 哪些环境变量会暴露给客户端？", "Vite 环境变量官方摘要", ("VITE_",), ("nodeIntegration",)),
    BenchmarkCase("vite env access", "Vite 源码里怎么读取环境变量？", "Vite 环境变量官方摘要", ("import.meta.env",), ("TestClient(app)",)),
    BenchmarkCase("vite env string", "Vite 环境变量值是什么类型？", "Vite 环境变量官方摘要", ("字符串",), ("Object.is",)),
    BenchmarkCase("vite restart", "Vite 修改 .env 文件后要做什么？", "Vite 环境变量官方摘要", ("重启开发服务器",), ("uvicorn",)),
    BenchmarkCase("electron no node integration", "Electron 加载远程内容时 nodeIntegration 应该怎么设置？", "Electron 安全配置官方摘要", ("不要启用 nodeIntegration",), ("VITE_",)),
    BenchmarkCase("electron context isolation", "Electron contextIsolation 为什么要开？", "Electron 安全配置官方摘要", ("preload 与网页运行在不同上下文",), ("MATCH",)),
    BenchmarkCase("electron preload whitelist", "Electron preload 应该暴露什么 API？", "Electron 安全配置官方摘要", ("最小白名单 API",), ("完整 Key",)),
    BenchmarkCase("electron ipc boundary", "Electron 主进程处理 IPC 要校验什么？", "Electron 安全配置官方摘要", ("消息来源和参数",), ("Object.is",)),
    BenchmarkCase("fastapi import client", "FastAPI 测试客户端从哪里导入？", "FastAPI TestClient 官方摘要", ("fastapi.testclient", "TestClient"), ("contextBridge",)),
    BenchmarkCase("fastapi wrap app", "FastAPI TestClient 怎么包装应用？", "FastAPI TestClient 官方摘要", ("TestClient(app)",), ("CREATE VIRTUAL TABLE",)),
    BenchmarkCase("fastapi no uvicorn", "FastAPI TestClient 需要单独启动 uvicorn 吗？", "FastAPI TestClient 官方摘要", ("不需要单独启动 uvicorn",), ("publish never",)),
    BenchmarkCase("sqlite fts create", "SQLite FTS5 怎么创建全文虚表？", "SQLite FTS5 BM25 官方摘要", ("CREATE VIRTUAL TABLE docs USING fts5(title, body)",), ("TestClient",)),
    BenchmarkCase("sqlite fts match", "SQLite FTS5 全文查询用什么表达式？", "SQLite FTS5 BM25 官方摘要", ("MATCH",), ("fetch()",)),
    BenchmarkCase("sqlite bm25 order", "SQLite FTS5 bm25 排序方向是什么？", "SQLite FTS5 BM25 官方摘要", ("分数越小表示匹配越好", "ORDER BY bm25"), ("VITE_",)),
    BenchmarkCase("sqlite delete boundary", "SQLite FTS5 删除资料后旧 chunk 还能 MATCH 吗？", "SQLite FTS5 BM25 官方摘要", ("不能让旧 chunk 继续参与 MATCH",), ("cleanup",)),
    BenchmarkCase("ollama local address", "Ollama 默认本地服务地址是什么？", "Ollama Embeddings 官方摘要", ("http://127.0.0.1:11434",), ("https://api.deepseek.com",)),
    BenchmarkCase("ollama embed endpoint", "Ollama 生成 embedding 用哪个端点？", "Ollama Embeddings 官方摘要", ("/api/embed",), ("/chat/completions",)),
    BenchmarkCase("ollama embed input", "Ollama /api/embed 请求体需要哪些字段？", "Ollama Embeddings 官方摘要", ("model", "input"), ("GITHUB_TOKEN",)),
    BenchmarkCase("ollama local privacy", "本地 Ollama embedding 的隐私边界是什么？", "Ollama Embeddings 官方摘要", ("不需要把资料片段发送给远程 embedding 服务商",), ("Bearer API Key",)),
    BenchmarkCase("deepseek base url", "DeepSeek API 的 Base URL 是什么？", "DeepSeek API 官方摘要", ("https://api.deepseek.com",), ("http://127.0.0.1:11434",)),
    BenchmarkCase("deepseek chat endpoint", "DeepSeek Chat Completions 使用哪个路径？", "DeepSeek API 官方摘要", ("/chat/completions",), ("/api/embed",)),
    BenchmarkCase("deepseek auth header", "DeepSeek API 认证边界怎么写？", "DeepSeek API 官方摘要", ("Authorization header", "Bearer API Key"), ("GITHUB_TOKEN",)),
    BenchmarkCase("deepseek rag boundary", "DeepSeek RAG 请求可能会收到什么内容？", "DeepSeek API 官方摘要", ("用户问题", "聊天上下文", "知识片段"), ("Object.is",)),
    BenchmarkCase("fetch promise", "MDN Fetch API 说 fetch() 成功时返回什么？", "MDN Fetch API 官方摘要", ("Promise", "Response"), ("TestClient(app)",)),
    BenchmarkCase("fetch http error", "fetch 遇到 404 或 500 会自动 reject 吗？", "MDN Fetch API 官方摘要", ("不会自动让 Promise reject",), ("cleanup",)),
    BenchmarkCase("fetch ok check", "fetch 业务代码应该检查哪个字段判断错误？", "MDN Fetch API 官方摘要", ("response.ok", "response.status"), ("contents: write",)),
    BenchmarkCase("fetch json body", "fetch 发送 JSON 时通常怎么处理请求体？", "MDN Fetch API 官方摘要", ("Content-Type: application/json", "JSON.stringify"), ("Object.is",)),
    BenchmarkCase("github token auto", "GitHub Actions workflow job 会自动提供什么令牌？", "GitHub Actions 自动令牌官方摘要", ("GITHUB_TOKEN",), ("Bearer API Key",)),
    BenchmarkCase("github permissions", "GitHub Actions 怎么限制自动令牌权限？", "GitHub Actions 自动令牌官方摘要", ("permissions",), ("nodeIntegration",)),
    BenchmarkCase("github release permission", "GitHub Actions 上传 Release 资产通常需要什么权限？", "GitHub Actions 自动令牌官方摘要", ("contents: write",), ("Object.is",)),
    BenchmarkCase("github token logging", "GitHub Actions 自动令牌能打印到日志吗？", "GitHub Actions 自动令牌官方摘要", ("不要把令牌打印到日志",), ("VITE_",)),
    BenchmarkCase("python venv create", "Python venv 怎么创建 .venv？", "Python venv 官方摘要", ("python -m venv .venv",), ("TestClient",)),
    BenchmarkCase("python venv powershell", "Windows PowerShell 激活 venv 常见脚本是什么？", "Python venv 官方摘要", (".venv\\Scripts\\Activate.ps1",), ("latest.yml",)),
    BenchmarkCase("python venv isolation", "Python venv 的依赖边界是什么？", "Python venv 官方摘要", ("避免污染系统 Python",), ("VITE_",)),
    BenchmarkCase("tsconfig noemit", "TypeScript tsconfig 里 noEmit 有什么用？", "TypeScript TSConfig 官方摘要", ("只做类型检查", "不输出 JavaScript 文件"), ("uvicorn",)),
    BenchmarkCase("tsconfig strict", "TypeScript strict 会启用什么？", "TypeScript TSConfig 官方摘要", ("更严格的类型检查规则",), ("MATCH",)),
    BenchmarkCase("tsconfig include", "TypeScript tsconfig include 用来声明什么？", "TypeScript TSConfig 官方摘要", ("参与编译的文件匹配范围",), ("GITHUB_TOKEN",)),
    BenchmarkCase("electron builder targets", "electron-builder Windows 候选包会生成什么？", "Electron Builder 发布摘要", ("NSIS 安装包", "win-unpacked 目录"), ("Object.is",)),
    BenchmarkCase("electron builder publish never", "electron-builder 的 publish never 表示什么？", "Electron Builder 发布摘要", ("构建本地候选资产但不上传发布",), ("VITE_",)),
    BenchmarkCase("electron builder latest yml", "latest.yml 通常包含哪些自动更新元数据？", "Electron Builder 发布摘要", ("版本", "文件名", "sha512", "size"), ("response.ok",)),
    BenchmarkCase("generic base url", "Base URL 是什么？", None, should_inject=False, needs_clarification=True),
    BenchmarkCase("generic endpoint", "端点是什么？", None, should_inject=False, needs_clarification=True),
    BenchmarkCase("generic permission", "权限是什么？", None, should_inject=False, needs_clarification=True),
    BenchmarkCase("unrelated romance", "我今天心情不好应该怎么哄伴侣？", None, should_inject=False),
    BenchmarkCase("unrelated recipe", "番茄炒蛋怎么做？", None, should_inject=False),
    BenchmarkCase("unrelated travel", "周末适合去哪旅游？", None, should_inject=False),
]


PUBLIC_HYBRID_CASES = [
    BenchmarkCase("react cleanup paraphrase", "React 副作用重新同步前会先跑清理函数吗？", "React useEffect 官方摘要", ("先用旧值运行 cleanup",), ("VITE_",), retrieval_mode="hybrid"),
    BenchmarkCase("vite expose paraphrase", "前端代码能直接看到哪些 Vite 环境变量？", "Vite 环境变量官方摘要", ("VITE_",), ("GITHUB_TOKEN",), retrieval_mode="hybrid"),
    BenchmarkCase("electron bridge paraphrase", "Electron 页面能不能直接拿 ipcRenderer 和 fs？", "Electron 安全配置官方摘要", ("不要把 ipcRenderer 或 Node fs/path/process/shell 直接暴露给页面",), ("TestClient",), retrieval_mode="hybrid"),
    BenchmarkCase("fastapi in process paraphrase", "FastAPI 自动化测试是不是必须启动服务进程？", "FastAPI TestClient 官方摘要", ("不需要单独启动 uvicorn",), ("publish never",), retrieval_mode="hybrid"),
    BenchmarkCase("sqlite ranking paraphrase", "SQLite 全文检索哪个 bm25 分数更靠前？", "SQLite FTS5 BM25 官方摘要", ("分数越小表示匹配越好",), ("Object.is",), retrieval_mode="hybrid"),
    BenchmarkCase("ollama local embedding paraphrase", "想在本机算向量不发到云端，Ollama 摘要怎么说？", "Ollama Embeddings 官方摘要", ("不需要把资料片段发送给远程 embedding 服务商",), ("Bearer API Key",), retrieval_mode="hybrid"),
    BenchmarkCase("deepseek compatible paraphrase", "DeepSeek 调聊天接口按哪种兼容格式走？", "DeepSeek API 官方摘要", ("OpenAI 兼容", "/chat/completions"), ("GITHUB_TOKEN",), retrieval_mode="hybrid"),
    BenchmarkCase("fetch status paraphrase", "浏览器请求拿到 500 时是不是一定进 catch？", "MDN Fetch API 官方摘要", ("不会自动让 Promise reject", "response.ok"), ("contents: write",), retrieval_mode="hybrid"),
    BenchmarkCase("github least privilege paraphrase", "Actions 发布包时令牌权限应该怎么收紧？", "GitHub Actions 自动令牌官方摘要", ("permissions", "contents: write"), ("Bearer API Key",), retrieval_mode="hybrid"),
    BenchmarkCase("venv isolation paraphrase", "Python 项目依赖怎么避免装进系统解释器？", "Python venv 官方摘要", ("虚拟环境", "避免污染系统 Python"), ("latest.yml",), retrieval_mode="hybrid"),
    BenchmarkCase("tsc typecheck paraphrase", "TypeScript 只检查类型不产物输出用哪个配置？", "TypeScript TSConfig 官方摘要", ("noEmit", "不输出 JavaScript 文件"), ("MATCH",), retrieval_mode="hybrid"),
    BenchmarkCase("builder local candidate paraphrase", "桌面候选包怎么构建但不上传？", "Electron Builder 发布摘要", ("publish never", "不上传发布"), ("response.ok",), retrieval_mode="hybrid"),
]


def seed_public_documents(client: TestClient) -> None:
    for payload in PUBLIC_BENCHMARK_DOCUMENTS:
        response = client.post("/knowledge/sources", json=payload)
        assert response.status_code == 201


def evaluate_public_case(client: TestClient, case: BenchmarkCase, *, runtime: dict | None = None) -> str | None:
    return evaluate_case(client, case, runtime=runtime)


def test_public_official_docs_lexical_precision_and_no_answer_cases(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-public-docs.sqlite"))

    assert len(PUBLIC_DOCUMENTS) == 12
    assert len(PUBLIC_BENCHMARK_DOCUMENTS) >= 30
    assert len(PUBLIC_LEXICAL_CASES) >= 48

    with TestClient(app) as client:
        seed_public_documents(client)
        failures = [failure for case in PUBLIC_LEXICAL_CASES if (failure := evaluate_public_case(client, case))]

    assert not failures, "\n".join(failures)


def test_public_official_docs_hybrid_mock_embeddings(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-public-docs.sqlite"))
    runtime = public_runtime_config()

    assert len(PUBLIC_HYBRID_CASES) >= 12

    with TestClient(app) as client:
        seed_public_documents(client)
        reindex = client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": runtime})
        assert reindex.status_code == 200
        assert reindex.json()["failed"] == 0
        assert reindex.json()["indexed"] >= len(PUBLIC_BENCHMARK_DOCUMENTS)

        failures = [
            failure for case in PUBLIC_HYBRID_CASES if (failure := evaluate_public_case(client, case, runtime=runtime))
        ]

    assert not failures, "\n".join(failures)


def test_public_doc_table_row_and_source_metadata_are_chunked(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "rag-public-docs.sqlite"
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(db_path))

    with TestClient(app) as client:
        seed_public_documents(client)
        search = client.post("/knowledge/search", json={"query": "SQLite FTS5 bm25 排序方向是什么？", "topK": 3})
        assert search.status_code == 200
        assert search.json()["shouldInject"] is True

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT c.heading_path, c.chunk_type, c.content, c.metadata_json
            FROM knowledge_chunks c
            JOIN knowledge_sources s ON s.id = c.source_id
            WHERE s.title = 'SQLite FTS5 BM25 官方摘要'
            ORDER BY c.chunk_index
            """
        ).fetchall()

    assert rows
    assert any(row["chunk_type"] == "table_row" and "ORDER BY bm25(docs)" in row["content"] for row in rows)
    assert PUBLIC_SOURCE_URLS["SQLite FTS5 BM25 官方摘要"] == "https://www.sqlite.org/fts5.html"
    assert any("SQLite FTS5 BM25 官方摘要 / 全文检索" in row["heading_path"] for row in rows)


def test_public_deleted_source_is_not_recalled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-public-docs.sqlite"))

    with TestClient(app) as client:
        seed_public_documents(client)
        sources = client.get("/knowledge/sources").json()
        deepseek_source = next(source for source in sources if source["title"] == "DeepSeek API 官方摘要")
        deleted = client.delete(f"/knowledge/sources/{deepseek_source['id']}")
        assert deleted.status_code == 200

        search = client.post("/knowledge/search", json={"query": "DeepSeek API 的 Base URL 是什么？", "topK": 3})
        assert search.status_code == 200
        data = search.json()
        assert data["hits"] == []
        assert data["promptContext"] == ""
        assert data["shouldInject"] is False
