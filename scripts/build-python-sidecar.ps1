$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$backendRoot = Join-Path $projectRoot "backend"
$distRoot = Join-Path $backendRoot "dist"
$sidecarDist = Join-Path $distRoot "suoyi-backend"
$workRoot = Join-Path $backendRoot "build\pyinstaller"
$pythonExe = if ($env:PYTHON) { $env:PYTHON } else { Join-Path $projectRoot ".venv\Scripts\python.exe" }

function Resolve-ExistingOrParent([string]$path) {
  if (Test-Path -LiteralPath $path) {
    return (Resolve-Path -LiteralPath $path).Path
  }
  $parent = Split-Path -Parent $path
  if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent | Out-Null
  }
  return (Resolve-Path -LiteralPath $parent).Path
}

function Assert-UnderBackend([string]$path) {
  $backendResolved = (Resolve-Path -LiteralPath $backendRoot).Path
  $resolved = Resolve-ExistingOrParent $path
  if (-not $resolved.StartsWith($backendResolved, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to modify path outside backend: $path"
  }
}

if (-not (Test-Path -LiteralPath $pythonExe)) {
  throw "Python executable not found: $pythonExe. Create .venv and install backend requirements first."
}

Push-Location $projectRoot
try {
  & $pythonExe -m PyInstaller --version | Out-Null

  Assert-UnderBackend $sidecarDist
  Assert-UnderBackend $workRoot
  if (Test-Path -LiteralPath $sidecarDist) {
    Remove-Item -LiteralPath $sidecarDist -Recurse -Force
  }
  if (Test-Path -LiteralPath $workRoot) {
    Remove-Item -LiteralPath $workRoot -Recurse -Force
  }

  & $pythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --name suoyi-backend `
    --distpath $distRoot `
    --workpath $workRoot `
    --specpath $workRoot `
    --collect-submodules fastapi `
    --collect-submodules starlette `
    --collect-submodules pydantic `
    --collect-submodules uvicorn `
    --collect-submodules anyio `
    --hidden-import backend.app.main `
    --hidden-import backend.app.core `
    --hidden-import backend.app.db `
    --hidden-import backend.app.embeddings `
    --hidden-import backend.app.knowledge `
    --hidden-import backend.app.schemas `
    --exclude-module pytest `
    --exclude-module tests `
    backend\app\sidecar_entry.py

  $sidecarExe = Join-Path $sidecarDist "suoyi-backend.exe"
  if (-not (Test-Path -LiteralPath $sidecarExe)) {
    throw "PyInstaller finished but sidecar executable is missing: $sidecarExe"
  }

  Write-Host "Built Python sidecar: $sidecarExe"
}
finally {
  Pop-Location
}
