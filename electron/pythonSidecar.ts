import { app, ipcMain } from "electron";
import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";

type PythonBackendStatus = "idle" | "starting" | "available" | "unavailable" | "exited";

export type PythonBackendStatusPayload = {
  status: PythonBackendStatus;
  endpoint?: string;
  port?: number;
  managed: boolean;
  message: string;
};

type PythonSidecarOptions = {
  projectRoot: string;
  userDataPath: string;
  isPackaged: boolean;
};

type SidecarLaunchSpec =
  | {
      ok: true;
      executable: string;
      args: string[];
      cwd: string;
      startingMessage: string;
      availableMessage: string;
    }
  | {
      ok: false;
      message: string;
    };

const DEFAULT_PORT = 8765;
const MAX_PORT = 8780;
const HOST = "127.0.0.1";

let options: PythonSidecarOptions | null = null;
let childProcess: ChildProcess | null = null;
let startPromise: Promise<PythonBackendStatusPayload> | null = null;
let currentStatus: PythonBackendStatusPayload = {
  status: "idle",
  managed: false,
  message: "Python 后端尚未启动。",
};

function setStatus(next: PythonBackendStatusPayload): PythonBackendStatusPayload {
  currentStatus = next;
  return currentStatus;
}

function endpointForPort(port: number): string {
  return `http://${HOST}:${port}`;
}

function getPythonExecutable(projectRoot: string): string {
  return process.platform === "win32"
    ? path.join(projectRoot, ".venv", "Scripts", "python.exe")
    : path.join(projectRoot, ".venv", "bin", "python");
}

function getResourcesPath(): string {
  const electronProcess = process as NodeJS.Process & { resourcesPath?: string };
  return electronProcess.resourcesPath ?? path.join(options?.projectRoot ?? "", "..");
}

function getPackagedSidecarExecutable(): string {
  const executableName = process.platform === "win32" ? "suoyi-backend.exe" : "suoyi-backend";
  return path.join(getResourcesPath(), "python-backend", executableName);
}

function getSidecarLaunchSpec(nextOptions: PythonSidecarOptions, port: number): SidecarLaunchSpec {
  if (nextOptions.isPackaged) {
    const executable = getPackagedSidecarExecutable();
    if (!fs.existsSync(executable)) {
      return {
        ok: false,
        message: "当前安装包缺少 Python 后端资源，已保留 localStorage 回退。",
      };
    }
    return {
      ok: true,
      executable,
      args: ["--host", HOST, "--port", String(port)],
      cwd: path.dirname(executable),
      startingMessage: "正在启动随包 Python 后端...",
      availableMessage: "随包 Python 后端已由 Electron 托管。",
    };
  }

  const executable = getPythonExecutable(nextOptions.projectRoot);
  if (!fs.existsSync(executable)) {
    return {
      ok: false,
      message: "未找到项目 .venv Python，请先按 backend/README.md 安装依赖。",
    };
  }
  return {
    ok: true,
    executable,
    args: ["-m", "uvicorn", "backend.app.main:app", "--host", HOST, "--port", String(port)],
    cwd: nextOptions.projectRoot,
    startingMessage: "正在启动本机 Python 后端...",
    availableMessage: "Python 后端已由 Electron 托管。",
  };
}

function isPortFree(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close(() => resolve(true));
    });
    server.listen(port, HOST);
  });
}

async function checkHealth(endpoint: string, timeoutMs = 700): Promise<boolean> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${endpoint}/health`, { signal: controller.signal });
    if (!response.ok) return false;
    const data = (await response.json()) as { status?: unknown; dbReady?: unknown; schemaVersion?: unknown };
    const schemaVersion = typeof data.schemaVersion === "number" ? data.schemaVersion : 0;
    return data.status === "ok" && data.dbReady === true && schemaVersion >= 2;
  } catch {
    return false;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function waitForHealth(endpoint: string, timeoutMs = 10_000): Promise<boolean> {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    if (await checkHealth(endpoint, 900)) return true;
    await new Promise((resolve) => setTimeout(resolve, 350));
  }
  return false;
}

async function findPort(): Promise<{ port: number; endpoint: string } | null> {
  for (let port = DEFAULT_PORT; port <= MAX_PORT; port += 1) {
    const endpoint = endpointForPort(port);
    if (await isPortFree(port)) {
      return { port, endpoint };
    }
  }
  return null;
}

async function startSidecar(): Promise<PythonBackendStatusPayload> {
  if (!options) return currentStatus;
  if (startPromise) return startPromise;
  if (currentStatus.status === "available") return currentStatus;

  startPromise = (async () => {
    const portInfo = await findPort();
    if (!portInfo) {
      return setStatus({
        status: "unavailable",
        managed: false,
        message: "8765-8780 端口都不可用，Python 后端未启动。",
      });
    }

    const launchSpec = getSidecarLaunchSpec(options, portInfo.port);
    if (!launchSpec.ok) {
      return setStatus({
        status: "unavailable",
        managed: false,
        message: launchSpec.message,
      });
    }

    const dbPath = path.join(options.userDataPath, "backend", "suoyi.sqlite");
    fs.mkdirSync(path.dirname(dbPath), { recursive: true });
    setStatus({
      status: "starting",
      endpoint: portInfo.endpoint,
      port: portInfo.port,
      managed: true,
      message: launchSpec.startingMessage,
    });

    childProcess = spawn(
      launchSpec.executable,
      launchSpec.args,
      {
        cwd: launchSpec.cwd,
        env: {
          ...process.env,
          SUOYI_BACKEND_DB_PATH: dbPath,
        },
        stdio: "ignore",
        windowsHide: true,
      },
    );

    childProcess.once("error", () => {
      setStatus({
        status: "unavailable",
        managed: false,
        message: "Python 后端启动失败，已保留 localStorage 回退。",
      });
    });

    childProcess.once("exit", () => {
      childProcess = null;
      if (currentStatus.managed) {
        setStatus({
          status: "exited",
          managed: false,
          message: "Python 后端进程已退出，核心数据会回退到 localStorage。",
        });
      }
    });

    const ready = await waitForHealth(portInfo.endpoint);
    if (!ready) {
      stopPythonSidecar();
      return setStatus({
        status: "unavailable",
        managed: false,
        message: "Python 后端启动超时，已保留 localStorage 回退。",
      });
    }

    return setStatus({
      status: "available",
      endpoint: portInfo.endpoint,
      port: portInfo.port,
      managed: true,
      message: launchSpec.availableMessage,
    });
  })();

  try {
    return await startPromise;
  } finally {
    startPromise = null;
  }
}

export function initializePythonSidecar(nextOptions: PythonSidecarOptions): void {
  options = nextOptions;
  void startSidecar();
}

export async function getPythonSidecarStatus(): Promise<PythonBackendStatusPayload> {
  if (currentStatus.status === "starting" && startPromise) {
    return startPromise;
  }
  if (currentStatus.status === "idle" || currentStatus.status === "exited" || currentStatus.status === "unavailable") {
    return startSidecar();
  }
  if (currentStatus.endpoint && currentStatus.status === "available" && !(await checkHealth(currentStatus.endpoint))) {
    setStatus({
      status: "exited",
      managed: false,
      message: "Python 后端健康检查失败，核心数据会回退到 localStorage。",
    });
    return startSidecar();
  }
  return currentStatus;
}

export async function getPythonSidecarEndpoint(): Promise<string | null> {
  const status = await getPythonSidecarStatus();
  return status.endpoint ?? null;
}

export function stopPythonSidecar(): void {
  if (!childProcess) return;
  const processToKill = childProcess;
  childProcess = null;
  if (!processToKill.killed) {
    processToKill.kill();
  }
}

export function registerPythonSidecarIpc(): void {
  ipcMain.handle("python-backend:get-status", () => getPythonSidecarStatus());
  ipcMain.handle("python-backend:get-endpoint", () => getPythonSidecarEndpoint());

  app.once("before-quit", () => {
    stopPythonSidecar();
  });
}
