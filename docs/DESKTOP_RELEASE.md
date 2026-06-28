# 所依桌面版发布说明

v0.6-C 使用 Electron + electron-builder + electron-updater 作为 Windows 桌面版骨架。用户可见应用名、窗口标题、安装包名、快捷方式和开始菜单名称统一为“所依”。

## 构建命令

```bash
npm run desktop:dir
npm run desktop:dist
```

- `desktop:dir` 生成 unpacked 目录，便于快速验收。
- `desktop:dist` 生成 Windows NSIS 安装包 `.exe`。
- Web 版命令 `npm run dev`、`npm run build`、`启动AI伴侣.bat` 保留。
- 本轮输出目录为 `release-v06c/`，安装包名形如 `所依 Setup 0.1.0.exe`。

## 窗口与外观

- 桌面版移除 Electron 默认系统菜单栏，不显示 `File / Edit / View / Window / Help`。
- 桌面版使用无框窗口和自定义标题栏，右侧提供最小化、最大化/还原、关闭按钮。
- 标题栏空白区域可拖拽，窗口按钮和应用内交互区域不可拖拽。
- v0.6-C 只做桌面壳视觉、窗口控制、品牌改名和软件感收口；正式图标、代码签名、真实生产更新源和公开发布物料放到后续阶段。

## 数据与迁移

桌面版和浏览器版的 `localStorage` 是不同空间，不会自动读取 Chrome/Edge 数据。

推荐迁移方式：

1. 在网页版设置中导出配置/记忆 JSON。
2. 安装并打开所依桌面版。
3. 在桌面版设置中点击“从网页版导入备份”。
4. 导入会覆盖桌面版的伴侣、长期记忆、风格摘要和去 Key 的服务商配置。
5. API Key 不在导出文件里，桌面版需要重新填写。

Electron 的 `appId` 固定为 `com.ai-companion.desktop`。用户可见 `productName` 为 `所依`；为了保护 v0.6-B 已有桌面数据，内部 `userData` 目录继续使用原稳定目录。升级同一应用不会清空 userData。

## 更新机制

应用内设置页提供弱入口“检查更新”。默认不显示“更新”行动按钮。

- 无新版：只提示当前已是最新版本。
- 有新版：显示提示卡和“立即更新”按钮。
- 下载完成：显示“重启并安装”按钮。
- 取消：隐藏本轮更新行动按钮，可稍后再次检查。

当前 P0 发布源配置为本地测试 generic feed：

```text
http://127.0.0.1:51730/updates/
```

真实发布前需要替换为公开 GitHub Releases 或稳定 HTTPS generic 源，并上传 NSIS 安装包、`latest.yml` 和 blockmap 等 electron-builder 产物。

## 代码签名

当前没有配置 Windows 代码签名证书。本地安装包可以测试，但正式分发时 Windows SmartScreen 可能提示未知发布者。正式发布前建议评估代码签名证书。

## 隐私边界

- 不把 API Key 写入代码、构建配置、更新元数据、日志或 release notes。
- 导出 JSON 不包含 API Key，也不默认包含原始聊天记录。
- 更新只替换应用代码，不删除 userData。
