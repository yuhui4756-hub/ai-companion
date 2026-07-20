import { contextBridge, ipcRenderer } from "electron";

type UpdateStatusPayload = {
  status: string;
  version?: string;
  percent?: number;
  transferred?: number;
  total?: number;
  message?: string;
};

type ModelProviderConfig = {
  providerName: string;
  baseURL: string;
  apiKey: string;
  model: string;
};

type OpenAIChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

type PythonBackendStatusPayload = {
  status: "idle" | "starting" | "available" | "unavailable" | "exited";
  endpoint?: string;
  port?: number;
  managed: boolean;
  message: string;
};

contextBridge.exposeInMainWorld("aiCompanionDesktop", {
  getInfo: () => ipcRenderer.invoke("desktop:get-info"),
  modelProvider: {
    requestChatCompletion: (config: ModelProviderConfig, messages: OpenAIChatMessage[]) =>
      ipcRenderer.invoke("model-provider:request-chat-completion", { config, messages }),
  },
  pythonBackend: {
    getStatus: (): Promise<PythonBackendStatusPayload> => ipcRenderer.invoke("python-backend:get-status"),
    getEndpoint: (): Promise<string | null> => ipcRenderer.invoke("python-backend:get-endpoint"),
  },
  updates: {
    getStatus: () => ipcRenderer.invoke("updates:get-status"),
    check: (options?: { simulateAvailable?: boolean; silent?: boolean }) => ipcRenderer.invoke("updates:check", options),
    download: () => ipcRenderer.invoke("updates:download"),
    quitAndInstall: () => ipcRenderer.invoke("updates:quit-and-install"),
    onStatus: (callback: (payload: UpdateStatusPayload) => void) => {
      const listener = (_event: Electron.IpcRendererEvent, payload: UpdateStatusPayload) => callback(payload);
      ipcRenderer.on("updates:status", listener);
      return () => ipcRenderer.removeListener("updates:status", listener);
    },
  },
  windowControls: {
    minimize: () => ipcRenderer.invoke("desktop-window:minimize"),
    toggleMaximize: () => ipcRenderer.invoke("desktop-window:toggle-maximize"),
    close: () => ipcRenderer.invoke("desktop-window:close"),
    isMaximized: () => ipcRenderer.invoke("desktop-window:is-maximized"),
    onMaximizedChange: (callback: (isMaximized: boolean) => void) => {
      const listener = (_event: Electron.IpcRendererEvent, isMaximized: boolean) => callback(isMaximized);
      ipcRenderer.on("desktop-window:maximized-change", listener);
      return () => ipcRenderer.removeListener("desktop-window:maximized-change", listener);
    },
  },
});
