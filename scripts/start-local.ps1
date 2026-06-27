param(
  [ValidateSet("dev", "preview")]
  [string]$Mode = "dev"
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$AppUrl = "http://127.0.0.1:5173/"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

function Wait-BeforeExit {
  Write-Host ""
  Write-Host "按任意键关闭这个窗口..."
  try {
    if (-not [Console]::IsInputRedirected) {
      $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    } else {
      Start-Sleep -Seconds 2
    }
  } catch {
    Start-Sleep -Seconds 2
  }
}

function Test-CommandAvailable {
  param([string]$Name)
  return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-PortOpen {
  $client = New-Object System.Net.Sockets.TcpClient
  try {
    $connect = $client.BeginConnect("127.0.0.1", 5173, $null, $null)
    if (-not $connect.AsyncWaitHandle.WaitOne(300, $false)) {
      return $false
    }
    $client.EndConnect($connect)
    return $true
  } catch {
    return $false
  } finally {
    $client.Close()
  }
}

function Start-BrowserWhenReady {
  $openScript = @"
`$url = "$AppUrl"
for (`$i = 0; `$i -lt 30; `$i += 1) {
  try {
    Invoke-WebRequest -Uri `$url -UseBasicParsing -TimeoutSec 1 | Out-Null
    Start-Process `$url
    exit 0
  } catch {
    Start-Sleep -Milliseconds 500
  }
}
Start-Process `$url
"@
  $encoded = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($openScript))
  Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encoded) -WindowStyle Hidden | Out-Null
}

function Invoke-NpmLongRunningScript {
  param([string]$ScriptName)

  if ([Console]::IsInputRedirected) {
    $process = Start-Process -FilePath "npm.cmd" -ArgumentList @("run", $ScriptName) -WindowStyle Hidden -PassThru
    for ($i = 0; $i -lt 40; $i += 1) {
      if (Test-PortOpen) {
        Write-Host "本地服务已启动：$AppUrl"
        return 0
      }
      if ($process.HasExited) {
        return $process.ExitCode
      }
      Start-Sleep -Milliseconds 500
    }
    return 1
  }

  $process = Start-Process -FilePath "npm.cmd" -ArgumentList @("run", $ScriptName) -NoNewWindow -Wait -PassThru
  return $process.ExitCode
}

try {
  Set-Location -LiteralPath $ProjectRoot

  Write-Host "AI伴侣本地启动器"
  Write-Host "固定地址：$AppUrl"
  Write-Host ""

  if (-not (Test-CommandAvailable "node") -or -not (Test-CommandAvailable "npm")) {
    Write-Host "没有检测到 Node.js / npm。"
    Write-Host "请先安装 Node.js LTS 版本，然后重新双击启动脚本。"
    Write-Host "下载地址：https://nodejs.org/"
    Wait-BeforeExit
    exit 1
  }

  if (Test-PortOpen) {
    Write-Host "检测到 5173 端口已经在使用。"
    Write-Host "可能已经有一个 AI伴侣窗口/服务在运行。"
    Write-Host "现在为你打开固定地址；如果打不开，请关闭旧的命令窗口后重试。"
    Start-Process $AppUrl
    Wait-BeforeExit
    exit 0
  }

  if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "node_modules"))) {
    Write-Host "第一次运行需要安装依赖，正在执行 npm install..."
    npm install
    if ($LASTEXITCODE -ne 0) {
      throw "npm install 失败，请检查网络或 Node.js 安装状态。"
    }
  }

  if ($Mode -eq "preview") {
    Write-Host "正在构建项目..."
    npm run build
    if ($LASTEXITCODE -ne 0) {
      throw "构建失败，请先根据上方报错修复项目。"
    }

    Write-Host ""
    Write-Host "构建完成，正在预览构建版。"
    Write-Host "停止方式：回到这个窗口按 Ctrl + C，然后输入 Y。"
    Start-BrowserWhenReady
    $exitCode = Invoke-NpmLongRunningScript "preview"
  } else {
    Write-Host "正在启动开发版。"
    Write-Host "停止方式：回到这个窗口按 Ctrl + C，然后输入 Y。"
    Start-BrowserWhenReady
    $exitCode = Invoke-NpmLongRunningScript "dev"
  }

  if ($exitCode -ne 0 -and -not (Test-PortOpen)) {
    Write-Host ""
    Write-Host "本地服务已经停止。如果不是你主动关闭，请查看上方提示。"
    Wait-BeforeExit
    exit $exitCode
  }
} catch {
  Write-Host ""
  Write-Host "启动失败：$($_.Exception.Message)"
  Write-Host "如果看到端口占用提示，可以先打开 $AppUrl，或关闭旧命令窗口后重试。"
  Wait-BeforeExit
  exit 1
}
