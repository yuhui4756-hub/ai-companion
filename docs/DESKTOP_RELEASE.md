# 所依桌面版发布说明

v0.1.2 使用 Electron + electron-builder + electron-updater 作为 Windows 桌面版发布骨架。用户可见应用名、窗口标题、安装包名、快捷方式和开始菜单名称统一为“所依”。

## 构建命令

```bash
npm run backend:build-sidecar
npm run desktop:dir
npm run desktop:dist
```

- `desktop:dir` 生成 unpacked 目录，便于快速验收。
- `desktop:dist` 生成 Windows NSIS 安装包 `.exe`、`latest.yml` 和 blockmap。
- `desktop:dir` 和 `desktop:dist` 会先执行 `backend:build-sidecar`，用 PyInstaller onedir 生成 `backend/dist/suoyi-backend/`，再通过 electron-builder `extraResources` 内置到 `resources/python-backend/`。
- Web 版命令 `npm run dev`、`npm run build`、`启动AI伴侣.bat` 保留。
- 本轮输出目录为 `release-v06d/`，安装包名形如 `suoyi-setup-0.1.2.exe`；应用窗口、快捷方式和开始菜单显示名仍为“所依”。

## Python sidecar 候选资源

2C 采用 PyInstaller onedir 方案打包 Python/FastAPI 后端：

- 构建入口：`backend/app/sidecar_entry.py`。
- 构建脚本：`scripts/build-python-sidecar.ps1`。
- 构建依赖：`backend/requirements-build.txt`，只用于本地构建，不是运行依赖。
- 输出目录：`backend/dist/suoyi-backend/`，其中应包含 `suoyi-backend.exe`。
- 打包位置：`release-v06d/win-unpacked/resources/python-backend/`。

候选包运行时，Electron 会从 `process.resourcesPath/python-backend/suoyi-backend.exe` 启动后端，并传入 `--host 127.0.0.1 --port <port>`。默认尝试 `8765`，占用时尝试 `8766-8780`。SQLite 文件放在 Electron `userData/backend/suoyi.sqlite`，不放在安装目录或 `resources` 目录。

如果 exe 缺失、启动失败或健康检查失败，主窗口仍应打开；renderer 会显示本地后端不可用，并继续使用 legacy `localStorage` fallback。packaged 候选资源不得包含 `.venv`、`backend/data`、`.sqlite/.db`、`.env*`、测试 fixture 或真实用户数据。

## 图标

- 图标源图来自 `D:\QQ文件\9F948C72-FE6D-4892-A8E5-3A36E3F3CBC5.png`。
- 生成资源保存在 `build/icons/`：
  - `source.png`：原始源图副本。
  - `icon.png`：规范化 1024x1024 PNG，已裁掉过大的透明边距，避免 Windows 桌面快捷方式图标主体显得偏小。
  - `icon.ico`：Windows/Electron/NSIS 图标，包含 16、24、32、48、64、128、256 多尺寸。
- `electron-builder.yml` 已配置 `win.icon`、`nsis.installerIcon`、`nsis.uninstallerIcon`，主窗口也设置了同一图标。
- 应用内品牌区和标题栏的小图标也复用本地图标资源，不再使用旧爱心标识。

## 窗口与外观

- 桌面版移除 Electron 默认系统菜单栏，不显示 `File / Edit / View / Window / Help`。
- 桌面版使用无框窗口和自定义标题栏，右侧提供最小化、最大化/还原、关闭按钮。
- 标题栏空白区域可拖拽，窗口按钮和应用内交互区域不可拖拽。
- 标题栏只显示“所依”，不再显示当前伴侣名字。

## 数据与迁移

桌面版和浏览器版的 `localStorage` 是不同空间，不会自动读取 Chrome/Edge 数据。

推荐迁移方式：

1. 在网页版设置中导出配置/记忆 JSON。
2. 安装并打开所依桌面版。
3. 在桌面版设置中点击“从网页版导入备份”。
4. 导入会覆盖桌面版的伴侣、长期记忆、风格摘要和去 Key 的服务商配置。
5. API Key 不在导出文件里，桌面版需要重新填写。

Electron 的 `appId` 固定为 `com.ai-companion.desktop`。为了保护 v0.6-B/v0.6-C 已有桌面数据，内部 `userData` 目录继续使用原稳定目录。升级同一应用不会清空 userData。

## 更新机制

发布源准备为公开 GitHub Releases：

```yaml
publish:
  provider: github
  owner: yuhui4756-hub
  repo: ai-companion
```

客户端不内置 GitHub token。若发布端需要上传 release artifacts，`GH_TOKEN` 只能作为本机环境变量或 CI Secret 使用，不能写入源码、配置、`latest.yml` 或安装包。

应用启动后桌面版会静默检查一次更新：

- 无新版：不显示更新入口，不打扰聊天。
- 有新版：左上品牌区“本地恋爱陪伴”旁出现小圆形更新标识。
- 点击标识后弹出确认，用户点“立即更新”才下载。
- 下载完成后再次确认“重启安装”，不会无确认自动重启。
- 更新失败只给轻提示，不展示 token、堆栈或敏感参数。

公开 release artifacts 至少保留：

- `suoyi-setup-0.1.2.exe`
- `suoyi-setup-0.1.2.exe.blockmap`
- `latest.yml`

开发线程只负责生成本地 Release 候选资产，不直接创建或上传 GitHub Release。当前 `desktop:dist` 固定使用 `--publish never`，避免候选构建误上传。正式公开发布由总控确认后，在 GitHub Releases 中上传以上三个文件；不要手改 `latest.yml` 的 `sha512`、`size`、`path`。

`package.json.version` 决定应用版本和构建产物版本。测试自动更新必须使用不同版本号，例如先装 `0.1.1`，再发布 `0.1.2`，不要用同版本测试更新。

## v0.1.2 发布执行清单

用户已确认进入 `v0.1.2` 正式发布执行。本轮仍保持构建与上传分离：`desktop:dist` 只生成本地候选资产，不自动发布；总控核验后手动创建 GitHub Release 并上传正式资产。

建议正式发布目标：

- 目标版本：`0.1.2`。
- 发布 tag：`v0.1.2`。
- Release name：`所依 v0.1.2`。
- 正式上传资产：
  - `release-v06d/suoyi-setup-0.1.2.exe`
  - `release-v06d/suoyi-setup-0.1.2.exe.blockmap`
  - `release-v06d/latest.yml`

发布前本地核验：

```powershell
npm run desktop:dist
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify-release-candidate.ps1 -ExpectedVersion 0.1.2
```

如果本机到 GitHub 的大文件上传链路不稳定，可以在 GitHub Actions 手动触发 `Release desktop` workflow。该 workflow 会按指定 tag 在 Windows runner 上重新构建、核验并上传正式资产，避免把本机 `GH_TOKEN` 或候选包路径写进源码。

核验脚本只读检查本地 `release-v06d/`，不会上传文件、不会调用 `gh release create/upload`，也不会读取或打印 `GH_TOKEN`。它会检查安装包、blockmap、`latest.yml`、`win-unpacked/resources/python-backend/suoyi-backend.exe` 是否存在，并核对 `latest.yml` 中的 `version`、`path/url`、`sha512`、`size` 与安装包文件是否一致；同时拒绝 `.sqlite/.db`、`.env*`、`.venv`、`backend/data` 和常见密钥形态进入候选目录。不要手改 `latest.yml` 的 `sha512`、`size` 或 `path`。

## 正式发布执行步骤

以下动作会改变真实发布状态，只能由总控在用户确认后执行：

1. 将 `package.json.version` 从 `0.1.1` 升到 `0.1.2`；如果存在 `package-lock.json`，其中根包版本也必须同步。
2. 重新运行 `npm run desktop:dist`，确认产物文件名变为 `suoyi-setup-0.1.2.exe`、`suoyi-setup-0.1.2.exe.blockmap`，且 `latest.yml` 的 `version/path/sha512/size` 指向 `0.1.2` 产物。
3. 运行 `scripts/verify-release-candidate.ps1 -ExpectedVersion 0.1.2` 和密钥扫描，确认候选资产不含真实 API Key、GitHub token、Cookie、扫码凭证或用户 SQLite 数据。
4. 创建或更新 GitHub Release `v0.1.2`，上传上面三个正式资产。
5. 上传前后核对远端 assets 名称、大小、公开下载 URL，以及远端 `latest.yml` 内容。`GH_TOKEN` 只能由总控/CI 在发布端环境变量或 Secret 使用，不得写入源码、文档、日志、`latest.yml` 或安装包。
6. 在公开下载可读后，再更新 `README.md` 下载链接和 Release 页面链接。

## Release notes 模板

```md
# 所依 v0.1.2

本版继续保持本地优先和 BYOK 使用方式，重点补齐桌面端工程化能力。

## 主要更新

- 内置 Python/FastAPI 本地后端 sidecar，桌面安装包不再要求用户手动安装 Python 或 `.venv`。
- 新增本机 SQLite 数据层，可把旧 `localStorage` 中的伴侣、聊天、长期记忆、风格摘要和去 Key 的模型配置复制迁移到本地数据库。
- 新增本地知识库/RAG：用户可手动导入文本或 Markdown，相关聊天时只注入命中的“用户导入资料”片段，删除资料后不再注入。
- 旧 `localStorage` 保留为 fallback；迁移失败或本地后端不可用时，聊天主流程仍可继续使用旧数据。

## 隐私与数据边界

- API Key 不写入 SQLite；provider 配置只保存去 Key 字段和 `renderer-localStorage` 引用。
- 没有云账号、没有云同步，也不会把完整数据库、完整 localStorage 快照或知识库全集上传到自有服务器。
- 模型请求仍只发给用户自己配置的模型服务商；请求内容可能包含当前聊天上下文、长期记忆/风格摘要和本次命中的知识片段。

## 已知边界

- 当前仍未配置 Windows 代码签名证书，安装时可能出现“未知发布者”或 SmartScreen 提示。
- 本次发布不代表工程化 P0 全量完成，后续仍可继续完善细粒度 CRUD、恢复/清理 UI、SQLite 加密或 OS 安全存储。
```

Release body 不要包含真实日志、真实密钥、用户数据、GitHub token，也不要承诺“工程化 P0 全量完成”。

## 自动更新验收步骤

正式发布后再做端到端自动更新验收：

1. 安装公开 `v0.1.1`。
2. 在同一 `appId=com.ai-companion.desktop`、同一 `userData=AppData/Roaming/AI伴侣` 下写入可识别 marker，例如新建伴侣、记忆或本地设置。
3. 总控确认 `v0.1.2` Release 已公开，且 `latest.yml`、安装包、blockmap 都可下载。
4. 启动 `v0.1.1`，观察更新状态从 available 到 downloaded，并由用户确认 `quitAndInstall`。
5. 重启后确认应用版本为 `0.1.2`，packaged sidecar `/health` 返回 schemaVersion >= 2。
6. 确认旧 marker、Electron localStorage、`userData/backend/suoyi.sqlite` 没有被清空；首次迁移失败时仍 fallback 到 localStorage。
7. 确认 SQLite、日志、错误提示、导出文件和 Release 元数据中没有明文 API Key/token/Cookie/扫码凭证。

## 回滚边界

- 从 `v0.1.1` 升级到 `v0.1.2` 时，同一 `appId` 和 `userData` 必须保持不变；更新只替换应用代码和随包 resources，不删除 Electron localStorage，也不删除 `userData/backend/suoyi.sqlite`。
- 首次运行新版时可把旧 localStorage snapshot 复制到 SQLite；失败时 fallback localStorage，不做破坏性迁移。
- 若 `v0.1.2` 公开后发现严重问题，保留旧 `v0.1.1` Release 作为手动下载回退点；已经升级到高版本的客户端通常不会自动降级到 `0.1.1`，不要承诺自动降级。
- 线上修复优先发布 `v0.1.3` hotfix；撤下、标记坏 Release、删除或替换远端资产都必须交回总控确认。

## 代码签名

当前没有配置 Windows 代码签名证书。本地安装包可以测试，但正式分发时 Windows SmartScreen 可能提示未知发布者。不要引导用户关闭安全防护；后续阶段再评估代码签名。

## 隐私边界

- 不把 API Key、GitHub token 写入代码、构建配置、更新元数据、日志或 release notes。
- 导出 JSON 不包含 API Key，也不默认包含原始聊天记录。
- 更新只替换应用代码，不删除 userData。
- 不自动读取 Chrome/Edge localStorage。
- Python sidecar 不接收、不保存、不转发模型 API Key；SQLite 的 provider_configs 只保存去 Key 字段和 `api_key_ref=renderer-localStorage`。
