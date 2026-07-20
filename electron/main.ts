import { app, BrowserWindow, ipcMain, Menu, shell } from "electron";
import path from "node:path";
import { registerModelProviderIpc } from "./modelProviderProxy";
import { initializePythonSidecar, registerPythonSidecarIpc } from "./pythonSidecar";
import { registerUpdaterIpc } from "./updater";

let mainWindow: BrowserWindow | null = null;

const APP_NAME = "所依";
const STABLE_USER_DATA_DIR = "AI伴侣";
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
  const windowIcon = path.join(__dirname, "..", "build", "icons", "icon.ico");
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 780,
    minWidth: 980,
    minHeight: 640,
    title: APP_NAME,
    frame: false,
    icon: windowIcon,
    backgroundColor: "#f4fbff",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
    },
  });

  const sendWindowState = () => {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    mainWindow.webContents.send("desktop-window:maximized-change", mainWindow.isMaximized());
  };

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

  mainWindow.on("maximize", sendWindowState);
  mainWindow.on("unmaximize", sendWindowState);
}

app.setName(APP_NAME);
app.setPath("userData", path.join(app.getPath("appData"), STABLE_USER_DATA_DIR));

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (!mainWindow) return;
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  });

  app.whenReady().then(() => {
    Menu.setApplicationMenu(null);

    ipcMain.handle("desktop:get-info", () => ({
      appName: app.getName(),
      version: app.getVersion(),
      platform: process.platform,
      isPackaged: app.isPackaged,
      userDataPath: app.getPath("userData"),
    }));

    ipcMain.handle("desktop-window:minimize", () => {
      mainWindow?.minimize();
    });

    ipcMain.handle("desktop-window:toggle-maximize", () => {
      if (!mainWindow) return false;
      if (mainWindow.isMaximized()) {
        mainWindow.unmaximize();
      } else {
        mainWindow.maximize();
      }
      return mainWindow.isMaximized();
    });

    ipcMain.handle("desktop-window:close", () => {
      mainWindow?.close();
    });

    ipcMain.handle("desktop-window:is-maximized", () => mainWindow?.isMaximized() ?? false);

    initializePythonSidecar({
      projectRoot: path.join(__dirname, ".."),
      userDataPath: app.getPath("userData"),
      isPackaged: app.isPackaged,
    });
    registerPythonSidecarIpc();
    registerModelProviderIpc();
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
