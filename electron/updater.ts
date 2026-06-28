import { app, BrowserWindow, ipcMain } from "electron";
import { autoUpdater } from "electron-updater";

type UpdateStatus =
  | "idle"
  | "checking"
  | "not-available"
  | "available"
  | "downloading"
  | "downloaded"
  | "error"
  | "not-configured";

type UpdatePayload = {
  status: UpdateStatus;
  version?: string;
  percent?: number;
  transferred?: number;
  total?: number;
  message?: string;
};

let lastStatus: UpdatePayload = { status: "idle" };
let mockUpdateAvailable = false;

function sanitizeUpdateError(error: unknown): string {
  const raw = error instanceof Error ? error.message : String(error);
  if (/ENOTFOUND|ECONNREFUSED|404|Cannot find channel|No published versions/i.test(raw)) {
    return "暂未连接到可用的发布源，请稍后再试或使用手动安装包更新。";
  }
  return "检查更新失败，请确认网络或发布源配置后再试。";
}

function sendStatus(window: BrowserWindow | null, payload: UpdatePayload): UpdatePayload {
  lastStatus = payload;
  if (window && !window.isDestroyed()) {
    window.webContents.send("updates:status", payload);
  }
  return payload;
}

export function registerUpdaterIpc(getWindow: () => BrowserWindow | null): void {
  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = false;

  autoUpdater.on("checking-for-update", () => {
    sendStatus(getWindow(), { status: "checking" });
  });

  autoUpdater.on("update-available", (info) => {
    sendStatus(getWindow(), { status: "available", version: info.version });
  });

  autoUpdater.on("update-not-available", () => {
    sendStatus(getWindow(), { status: "not-available", version: app.getVersion() });
  });

  autoUpdater.on("download-progress", (progress) => {
    sendStatus(getWindow(), {
      status: "downloading",
      percent: progress.percent,
      transferred: progress.transferred,
      total: progress.total,
    });
  });

  autoUpdater.on("update-downloaded", (info) => {
    sendStatus(getWindow(), { status: "downloaded", version: info.version });
  });

  autoUpdater.on("error", (error) => {
    sendStatus(getWindow(), { status: "error", message: sanitizeUpdateError(error) });
  });

  ipcMain.handle("updates:get-status", () => lastStatus);

  ipcMain.handle("updates:check", async (_event, options?: { simulateAvailable?: boolean; silent?: boolean }) => {
    if (options?.simulateAvailable && !app.isPackaged) {
      mockUpdateAvailable = true;
      return sendStatus(getWindow(), { status: "available", version: `${app.getVersion()}-dev-test` });
    }

    if (!app.isPackaged) {
      return sendStatus(getWindow(), {
        status: "not-configured",
        version: app.getVersion(),
        message: "开发模式不会连接真实发布源；可用“模拟新版提示”检查更新 UI。",
      });
    }

    if (!options?.silent) {
      sendStatus(getWindow(), { status: "checking" });
    }
    try {
      const result = await autoUpdater.checkForUpdates();
      if (!result) {
        return sendStatus(getWindow(), {
          status: "not-configured",
          message: "暂未配置可用发布源，请使用安装包手动更新。",
        });
      }
      return lastStatus;
    } catch (error) {
      return sendStatus(getWindow(), { status: "error", message: sanitizeUpdateError(error) });
    }
  });

  ipcMain.handle("updates:download", async () => {
    if (mockUpdateAvailable && !app.isPackaged) {
      return sendStatus(getWindow(), { status: "downloaded", version: `${app.getVersion()}-dev-test` });
    }

    if (!app.isPackaged) {
      return sendStatus(getWindow(), {
        status: "not-configured",
        message: "开发模式不能下载真实更新包。",
      });
    }

    sendStatus(getWindow(), { status: "downloading", percent: 0 });
    try {
      await autoUpdater.downloadUpdate();
      return lastStatus;
    } catch (error) {
      return sendStatus(getWindow(), { status: "error", message: sanitizeUpdateError(error) });
    }
  });

  ipcMain.handle("updates:quit-and-install", () => {
    if (mockUpdateAvailable && !app.isPackaged) {
      mockUpdateAvailable = false;
      return sendStatus(getWindow(), {
        status: "not-configured",
        message: "开发测试已模拟到安装前一步；真实安装需要已发布的更新包。",
      });
    }

    if (!app.isPackaged) {
      return sendStatus(getWindow(), {
        status: "not-configured",
        message: "开发模式不会重启安装更新。",
      });
    }

    autoUpdater.quitAndInstall(false, true);
    return lastStatus;
  });
}
