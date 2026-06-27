import { app, BrowserWindow, ipcMain, shell } from "electron";
import path from "node:path";
import { registerUpdaterIpc } from "./updater";

let mainWindow: BrowserWindow | null = null;

const isDevelopment = !app.isPackaged && Boolean(process.env.ELECTRON_RENDERER_URL);

function getAppUrl(): string {
  return process.env.ELECTRON_RENDERER_URL ?? "";
}

function isAllowedAppNavigation(url: string): boolean {
  if (isDevelopment) {
    return url.startsWith(getAppUrl());
  }
  return url.startsWith("file://");
}

function createMainWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 780,
    minWidth: 980,
    minHeight: 640,
    title: "AI伴侣",
    backgroundColor: "#f4fbff",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
    },
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    try {
      const parsed = new URL(url);
      if (parsed.protocol === "https:" || parsed.protocol === "mailto:") {
        shell.openExternal(url);
      }
    } catch {
      // Ignore malformed external navigation.
    }
    return { action: "deny" };
  });

  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (isAllowedAppNavigation(url)) return;
    event.preventDefault();
    try {
      const parsed = new URL(url);
      if (parsed.protocol === "https:" || parsed.protocol === "mailto:") {
        shell.openExternal(url);
      }
    } catch {
      // Ignore malformed external navigation.
    }
  });

  if (isDevelopment) {
    mainWindow.loadURL(getAppUrl());
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWindow.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.setName("AI伴侣");

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (!mainWindow) return;
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  });

  app.whenReady().then(() => {
    ipcMain.handle("desktop:get-info", () => ({
      appName: app.getName(),
      version: app.getVersion(),
      platform: process.platform,
      isPackaged: app.isPackaged,
      userDataPath: app.getPath("userData"),
    }));

    registerUpdaterIpc(() => mainWindow);
    createMainWindow();
  });
}

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createMainWindow();
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

