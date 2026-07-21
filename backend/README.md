# 所依 Python 本地后端

这是工程化第二轮的本机 sidecar backend，负责本地 SQLite 数据、知识库切分检索和核心数据快照迁移。它不接收、不保存、不转发模型 API Key。

## 启动

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8765
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
Invoke-RestMethod http://127.0.0.1:8765/core/status
```

默认数据库位于 `backend/data/suoyi-dev.sqlite`，可用环境变量 `SUOYI_BACKEND_DB_PATH` 覆盖。`backend/data/`、`.sqlite`、`.db` 文件不会提交进仓库。

## 打包为桌面 sidecar

2C 的桌面候选资产使用 PyInstaller onedir，把后端打成 `backend/dist/suoyi-backend/suoyi-backend.exe`。PyInstaller 只是构建依赖，不是运行依赖：

```powershell
.\.venv\Scripts\python -m pip install -r backend\requirements-build.txt
npm run backend:build-sidecar
```

构建输出只应包含 `suoyi-backend.exe` 和运行依赖，不应包含 `backend/data/`、`.sqlite/.db`、`.env`、`.venv`、测试 fixture 或真实用户数据。桌面候选包会通过 electron-builder `extraResources` 把该目录复制到 `resources/python-backend/`。

可手动检查 exe：

```powershell
.\backend\dist\suoyi-backend\suoyi-backend.exe --host 127.0.0.1 --port 8765
Invoke-RestMethod http://127.0.0.1:8765/health
```

桌面候选资产发布前 smoke：

```powershell
npm run desktop:dist
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify-release-candidate.ps1 -ExpectedVersion 0.1.1
```

如果总控后续确认发布 `0.1.2`，需先同步 bump `package.json` 和 `package-lock.json`，再重新构建并用 `-ExpectedVersion 0.1.2` 核验。该核验脚本只读检查本地 `release-v06d/`，不会上传 GitHub Release，也不会读取或打印 `GH_TOKEN`。当前候选包不等于公开新版。

## API 范围

- `GET /health`：返回服务和 SQLite schema 状态，不返回真实密钥。
- `GET /db/status`：返回知识库和核心数据计数。
- `POST /knowledge/sources`、`GET /knowledge/sources`、`DELETE /knowledge/sources/{source_id}`、`POST /knowledge/search`：2A 知识库/RAG 能力。
- `GET /core/status`：返回核心数据 SQLite 计数和最近一次 legacy snapshot 迁移状态。
- `GET /core/snapshot`：读取伴侣、消息、长期记忆、风格摘要和去 Key 的 provider 配置。
- `PUT /core/snapshot`：运行态保存当前核心快照，用于 SQLite 主存储同步。
- `POST /core/migrations/local-storage-snapshot`：从 renderer 提交去敏 legacy localStorage snapshot，后端用单事务幂等导入。

## 当前边界

- 只绑定本机 `127.0.0.1` 使用，不提供云服务。
- 知识库 sources/chunks、伴侣、聊天、长期记忆、风格摘要和去 Key 的 provider 配置会写入 SQLite；旧 localStorage 仍保留作回退。
- provider 配置只保存 `providerName`、`baseURL`、`model`、`options_json` 和 `api_key_ref`；明文 API Key 继续留在 renderer localStorage，不迁入 SQLite。
- 聊天时，前端只把最新用户输入发给本机后端做知识库检索；命中的知识片段会进入模型请求，并发给用户配置的模型服务商。
- 删除资料是软删除，不做不可撤销物理清理。
- Electron 开发态可以托管 `.venv` 里的 uvicorn 进程；桌面候选打包态可以托管 `resources/python-backend/suoyi-backend.exe`。当前公开安装包仍未发布新版；公开发布前必须再经过测试验收和总控确认。
