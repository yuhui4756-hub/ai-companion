# 所依桌面版发布说明

v0.1.1 使用 Electron + electron-builder + electron-updater 作为 Windows 桌面版发布骨架。用户可见应用名、窗口标题、安装包名、快捷方式和开始菜单名称统一为“所依”。

## 构建命令

```bash
npm run desktop:dir
npm run desktop:dist
```

- `desktop:dir` 生成 unpacked 目录，便于快速验收。
- `desktop:dist` 生成 Windows NSIS 安装包 `.exe`、`latest.yml` 和 blockmap。
- Web 版命令 `npm run dev`、`npm run build`、`启动AI伴侣.bat` 保留。
- 本轮输出目录为 `release-v06d/`，安装包名形如 `suoyi-setup-0.1.1.exe`；应用窗口、快捷方式和开始菜单显示名仍为“所依”。

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

- `suoyi-setup-0.1.1.exe`
- `suoyi-setup-0.1.1.exe.blockmap`
- `latest.yml`

开发线程只负责生成本地 Release 候选资产，不直接创建或上传 GitHub Release。正式公开发布由总控确认后，在 GitHub Releases 中上传以上三个文件；不要手改 `latest.yml` 的 `sha512`、`size`、`path`。

`package.json.version` 决定应用版本和构建产物版本。测试自动更新必须使用不同版本号，例如先装 `0.1.0`，再发布 `0.1.1`，不要用同版本测试更新。

## 代码签名

当前没有配置 Windows 代码签名证书。本地安装包可以测试，但正式分发时 Windows SmartScreen 可能提示未知发布者。不要引导用户关闭安全防护；后续阶段再评估代码签名。

## 隐私边界

- 不把 API Key、GitHub token 写入代码、构建配置、更新元数据、日志或 release notes。
- 导出 JSON 不包含 API Key，也不默认包含原始聊天记录。
- 更新只替换应用代码，不删除 userData。
- 不自动读取 Chrome/Edge localStorage。
