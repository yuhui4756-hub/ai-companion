import { contextBridge, ipcRenderer } from "electron";

type UpdateStatusPayload = {
  status: string;
  version?: string;
  percent?: number;
  transferred?: number;
  total?: number;
  message?: string;
};

contextBridge.exposeInMainWorld("aiCompanionDesktop", {
  getInfo: () => ipcRenderer.invoke("desktop:get-info"),
  updates: {
    getStatus: () => ipcRenderer.invoke("updates:get-status"),
    check: (options?: { simulateAvailable?: boolean }) => ipcRenderer.invoke("updates:check", options),
    download: () => ipcRenderer.invoke("updates:download"),
    quitAndInstall: () => ipcRenderer.invoke("updates:quit-and-install"),
    onStatus: (callback: (payload: UpdateStatusPayload) => void) => {
      const listener = (_event: Electron.IpcRendererEvent, payload: UpdateStatusPayload) => callback(payload);
      ipcRenderer.on("updates:status", listener);
      return () => ipcRenderer.removeListener("updates:status", listener);
    },
  },
});

