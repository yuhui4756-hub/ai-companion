# 所依 Python 本地后端

这是工程化第二轮的本机 sidecar backend，当前只负责知识库资料的 SQLite 保存、切分、检索和 prompt context 生成。它不接收、不保存、不转发模型 API Key。

## 启动

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8765
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
```

默认数据库位于 `backend/data/suoyi-dev.sqlite`，可用环境变量 `SUOYI_BACKEND_DB_PATH` 覆盖。`backend/data/`、`.sqlite`、`.db` 文件不会提交进仓库。

## 当前边界

- 只绑定本机 `127.0.0.1` 使用，不提供云服务。
- 只保存知识库 sources/chunks；伴侣、聊天、长期记忆、风格摘要、模型配置仍由现有前端 localStorage-backed repository 管理。
- 聊天时，前端只把最新用户输入发给本机后端做检索；命中的知识片段会进入模型请求，并发给用户配置的模型服务商。
- 删除资料是软删除，不做不可撤销物理清理。
