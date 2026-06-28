export type DesktopUpdateStatus =
  | "idle"
  | "checking"
  | "not-available"
  | "available"
  | "downloading"
  | "downloaded"
  | "error"
  | "not-configured";

export type DesktopUpdatePayload = {
  status: DesktopUpdateStatus;
  version?: string;
  percent?: number;
  transferred?: number;
  total?: number;
  message?: string;
};

export type DesktopInfo = {
  appName: string;
  version: string;
  platform: string;
  isPackaged: boolean;
  userDataPath: string;
};

export type DesktopBridge = {
  getInfo: () => Promise<DesktopInfo>;
  updates: {
    getStatus: () => Promise<DesktopUpdatePayload>;
    check: (options?: { simulateAvailable?: boolean }) => Promise<DesktopUpdatePayload>;
    download: () => Promise<DesktopUpdatePayload>;
    quitAndInstall: () => Promise<DesktopUpdatePayload>;
    onStatus: (callback: (payload: DesktopUpdatePayload) => void) => () => void;
  };
  windowControls?: {
    minimize: () => Promise<void>;
    toggleMaximize: () => Promise<boolean>;
    close: () => Promise<void>;
    isMaximized: () => Promise<boolean>;
    onMaximizedChange: (callback: (isMaximized: boolean) => void) => () => void;
  };
};

declare global {
  interface Window {
    aiCompanionDesktop?: DesktopBridge;
  }
}

export function getDesktopBridge(): DesktopBridge | undefined {
  return window.aiCompanionDesktop;
}
