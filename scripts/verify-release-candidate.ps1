param(
  [string]$ReleaseDir = "release-v06d",
  [string]$ExpectedVersion = "0.1.3",
  [int]$ExpectedSchemaVersion = 0
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$releasePath = Join-Path $projectRoot $ReleaseDir
$installerName = "suoyi-setup-$ExpectedVersion.exe"
$installerPath = Join-Path $releasePath $installerName
$blockmapPath = Join-Path $releasePath "$installerName.blockmap"
$latestPath = Join-Path $releasePath "latest.yml"
$sidecarPath = Join-Path $releasePath "win-unpacked\resources\python-backend\suoyi-backend.exe"

function Fail([string]$message) {
  throw "[release-candidate] $message"
}

function Pass([string]$message) {
  Write-Host "[ok] $message"
}

function Get-ReleaseRelativePath([string]$path) {
  $prefix = $releasePath.TrimEnd("\", "/")
  if ($path.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $path.Substring($prefix.Length).TrimStart("\", "/")
  }
  return $path
}

function Normalize-YamlScalar([string]$value) {
  $trimmed = $value.Trim()
  if ($trimmed.Length -ge 2) {
    $first = $trimmed.Substring(0, 1)
    $last = $trimmed.Substring($trimmed.Length - 1, 1)
    if (($first -eq "'" -and $last -eq "'") -or ($first -eq '"' -and $last -eq '"')) {
      return $trimmed.Substring(1, $trimmed.Length - 2)
    }
  }
  return $trimmed
}

function Get-YamlScalar([string]$content, [string]$name) {
  $pattern = "(?m)^\s*(?:-\s*)?$([regex]::Escape($name)):\s*(.+?)\s*$"
  $match = [regex]::Match($content, $pattern)
  if (-not $match.Success) {
    return $null
  }
  return Normalize-YamlScalar $match.Groups[1].Value
}

function Get-YamlScalars([string]$content, [string]$name) {
  $pattern = "(?m)^\s*(?:-\s*)?$([regex]::Escape($name)):\s*(.+?)\s*$"
  $matches = [regex]::Matches($content, $pattern)
  $values = @()
  foreach ($match in $matches) {
    $values += Normalize-YamlScalar $match.Groups[1].Value
  }
  return $values
}

function Get-Base64Sha512([string]$path) {
  $sha512 = [System.Security.Cryptography.SHA512]::Create()
  try {
    $stream = [System.IO.File]::OpenRead($path)
    try {
      return [Convert]::ToBase64String($sha512.ComputeHash($stream))
    }
    finally {
      $stream.Dispose()
    }
  }
  finally {
    $sha512.Dispose()
  }
}

function Test-KnownFalsePositive([string]$value) {
  return $value -eq "sk-loader-ios"
}

function Get-SourceSchemaVersion {
  $dbSourcePath = Join-Path $projectRoot "backend\app\db.py"
  if (-not (Test-Path -LiteralPath $dbSourcePath -PathType Leaf)) {
    Fail "Cannot infer schema version because backend/app/db.py is missing; pass -ExpectedSchemaVersion explicitly"
  }
  $dbSource = Get-Content -LiteralPath $dbSourcePath -Raw -Encoding UTF8
  $match = [regex]::Match($dbSource, "(?m)^\s*SCHEMA_VERSION\s*=\s*(\d+)\s*$")
  if (-not $match.Success) {
    Fail "Cannot infer schema version from backend/app/db.py; pass -ExpectedSchemaVersion explicitly"
  }
  return [int]$match.Groups[1].Value
}

function Test-LocalPortAvailable([int]$port) {
  $listener = $null
  try {
    $endpoint = New-Object System.Net.IPEndPoint ([System.Net.IPAddress]::Parse("127.0.0.1")), $port
    $listener = New-Object System.Net.Sockets.TcpListener $endpoint
    $listener.Start()
    return $true
  }
  catch {
    return $false
  }
  finally {
    if ($null -ne $listener) {
      $listener.Stop()
    }
  }
}

function Get-SidecarSmokePort {
  $ports = @(8780) + (8765..8779)
  foreach ($port in $ports) {
    if (Test-LocalPortAvailable $port) {
      return $port
    }
  }
  Fail "No available local port in 8765-8780 for packaged sidecar smoke"
}

function Test-HasJsonProperty($value, [string]$propertyName) {
  return $null -ne $value -and $value.PSObject.Properties.Name -contains $propertyName
}

function Invoke-SidecarJsonGet([string]$url) {
  return Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 2
}

function Invoke-PackagedSidecarSmoke([string]$exePath) {
  $port = Get-SidecarSmokePort
  $tempBase = [System.IO.Path]::GetTempPath()
  $tempDir = Join-Path $tempBase "suoyi-release-sidecar-smoke-$([guid]::NewGuid().ToString('N'))"
  $dbPath = Join-Path $tempDir "suoyi-smoke.sqlite"
  $oldDbPath = [Environment]::GetEnvironmentVariable("SUOYI_BACKEND_DB_PATH", "Process")
  $sidecarProcess = $null

  try {
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    [Environment]::SetEnvironmentVariable("SUOYI_BACKEND_DB_PATH", $dbPath, "Process")

    $sidecarProcess = Start-Process `
      -FilePath $exePath `
      -ArgumentList @("--host", "127.0.0.1", "--port", [string]$port) `
      -WorkingDirectory (Split-Path -Parent $exePath) `
      -PassThru `
      -WindowStyle Hidden

    $health = $null
    for ($index = 0; $index -lt 40; $index++) {
      if ($sidecarProcess.HasExited) {
        Fail "Packaged sidecar exited before health check completed with code $($sidecarProcess.ExitCode)"
      }
      try {
        $health = Invoke-SidecarJsonGet "http://127.0.0.1:$port/health"
        break
      }
      catch {
        Start-Sleep -Milliseconds 250
      }
    }
    if ($null -eq $health) {
      Fail "Packaged sidecar health check timed out on port $port"
    }
    if ($health.status -ne "ok") {
      Fail "Packaged sidecar /health status '$($health.status)' is not ok"
    }
    if ($health.dbReady -ne $true) {
      Fail "Packaged sidecar /health dbReady is not true"
    }
    if ([int]$health.schemaVersion -lt $ExpectedSchemaVersion) {
      Fail "Packaged sidecar schemaVersion '$($health.schemaVersion)' is lower than expected '$ExpectedSchemaVersion'"
    }

    $dbStatus = Invoke-SidecarJsonGet "http://127.0.0.1:$port/db/status"
    if (-not (Test-HasJsonProperty $dbStatus "ftsReady")) {
      Fail "Packaged sidecar /db/status missing ftsReady"
    }
    if (-not (Test-HasJsonProperty $dbStatus "knowledgeSearchMode")) {
      Fail "Packaged sidecar /db/status missing knowledgeSearchMode"
    }

    Pass "packaged sidecar smoke passed on port $port with schemaVersion $($health.schemaVersion)"
  }
  finally {
    if ($null -eq $oldDbPath) {
      [Environment]::SetEnvironmentVariable("SUOYI_BACKEND_DB_PATH", $null, "Process")
    }
    else {
      [Environment]::SetEnvironmentVariable("SUOYI_BACKEND_DB_PATH", $oldDbPath, "Process")
    }

    if ($null -ne $sidecarProcess -and -not $sidecarProcess.HasExited) {
      Stop-Process -Id $sidecarProcess.Id -Force -ErrorAction SilentlyContinue
      Wait-Process -Id $sidecarProcess.Id -Timeout 5 -ErrorAction SilentlyContinue
    }

    if (Test-Path -LiteralPath $tempDir) {
      $resolvedTempBase = (Resolve-Path -LiteralPath $tempBase).Path
      $resolvedTempDir = (Resolve-Path -LiteralPath $tempDir).Path
      if ($resolvedTempDir.StartsWith($resolvedTempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $resolvedTempDir -Recurse -Force -ErrorAction SilentlyContinue
      }
    }
  }
}

if (-not (Test-Path -LiteralPath $releasePath)) {
  Fail "Release directory not found: $releasePath"
}
$releasePath = (Resolve-Path -LiteralPath $releasePath).Path

if ($ExpectedSchemaVersion -le 0) {
  $ExpectedSchemaVersion = Get-SourceSchemaVersion
}

foreach ($requiredPath in @($installerPath, $blockmapPath, $latestPath, $sidecarPath)) {
  if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
    Fail "Required candidate file is missing: $(Get-ReleaseRelativePath $requiredPath)"
  }
}
Pass "required installer, blockmap, latest.yml, and packaged sidecar are present"

Invoke-PackagedSidecarSmoke $sidecarPath

$latestContent = Get-Content -LiteralPath $latestPath -Raw -Encoding UTF8
$version = Get-YamlScalar $latestContent "version"
$path = Get-YamlScalar $latestContent "path"
$urls = Get-YamlScalars $latestContent "url"
$shaValues = Get-YamlScalars $latestContent "sha512"
$sizeValues = Get-YamlScalars $latestContent "size"

if ($version -ne $ExpectedVersion) {
  Fail "latest.yml version '$version' does not match expected '$ExpectedVersion'"
}
if ($path -ne $installerName) {
  Fail "latest.yml path '$path' does not match installer '$installerName'"
}
if ($urls.Count -lt 1) {
  Fail "latest.yml has no files.url entry"
}
foreach ($url in $urls) {
  if ($url -ne $installerName) {
    Fail "latest.yml file url '$url' does not match installer '$installerName'"
  }
}

$installer = Get-Item -LiteralPath $installerPath
if ($sizeValues.Count -lt 1) {
  Fail "latest.yml has no size entry"
}
foreach ($sizeValue in $sizeValues) {
  $parsedSize = 0L
  if (-not [Int64]::TryParse($sizeValue, [ref]$parsedSize)) {
    Fail "latest.yml size '$sizeValue' is not an integer"
  }
  if ($parsedSize -ne $installer.Length) {
    Fail "latest.yml size '$parsedSize' does not match installer size '$($installer.Length)'"
  }
}

if ($shaValues.Count -lt 1) {
  Fail "latest.yml has no sha512 entry"
}
$computedSha512 = Get-Base64Sha512 $installerPath
foreach ($shaValue in $shaValues) {
  if ($shaValue -ne $computedSha512) {
    Fail "latest.yml sha512 does not match installer content"
  }
}
Pass "latest.yml version, path/url, size, and sha512 match $installerName"

$forbiddenItems = @()
$allItems = Get-ChildItem -LiteralPath $releasePath -Recurse -Force
foreach ($item in $allItems) {
  $relative = (Get-ReleaseRelativePath $item.FullName) -replace "\\", "/"
  if ($relative -match "(^|/)\.venv(/|$)") {
    $forbiddenItems += $relative
    continue
  }
  if ($relative -match "(^|/)backend/data(/|$)") {
    $forbiddenItems += $relative
    continue
  }
  if (-not $item.PSIsContainer) {
    if ($item.Name -eq ".env" -or $item.Name -like ".env.*") {
      $forbiddenItems += $relative
      continue
    }
    if ($item.Extension -match "^\.(sqlite|sqlite3|db)$") {
      $forbiddenItems += $relative
      continue
    }
  }
}
if ($forbiddenItems.Count -gt 0) {
  Fail "Forbidden files or directories found in candidate: $($forbiddenItems -join ', ')"
}
Pass "no SQLite DB, .env, .venv, or backend/data artifacts found in release directory"

$textExtensions = @(
  ".bat", ".cmd", ".config", ".css", ".html", ".ini", ".js", ".json", ".license",
  ".log", ".map", ".md", ".ps1", ".txt", ".toml", ".xml", ".yaml", ".yml"
)
$secretPatterns = @(
  @{ Name = "OpenAI-style API key"; Pattern = "sk-[A-Za-z0-9_-]{8,}" },
  @{ Name = "Bearer token"; Pattern = "Bearer\s+[A-Za-z0-9._~+/=-]{8,}" },
  @{ Name = "GitHub token"; Pattern = "github_pat_[A-Za-z0-9_]+" },
  @{ Name = "GH_TOKEN marker"; Pattern = "\bGH_TOKEN\b" },
  @{ Name = "x-api-key value"; Pattern = "(?i)\bx-api-key\b\s*[:=]\s*['""]?[A-Za-z0-9._~+/=-]{8,}" },
  @{ Name = "api key value"; Pattern = "(?i)\bapi[_-]?key\b\s*[:=]\s*['""]?[A-Za-z0-9._~+/=-]{8,}" },
  @{ Name = "access token value"; Pattern = "(?i)\baccess[_-]?token\b\s*[:=]\s*['""]?[A-Za-z0-9._~+/=-]{8,}" },
  @{ Name = "cookie value"; Pattern = "(?i)\bcookie\b\s*[:=]\s*['""]?[A-Za-z0-9._~+/=-]{8,}" }
)

$secretHits = @()
$candidateTextFiles = Get-ChildItem -LiteralPath $releasePath -Recurse -Force -File |
  Where-Object {
    $extension = $_.Extension.ToLowerInvariant()
    $textExtensions -contains $extension -and $_.Length -le 20MB
  }

foreach ($file in $candidateTextFiles) {
  $content = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
  if ($null -eq $content) {
    continue
  }
  foreach ($secretPattern in $secretPatterns) {
    $matches = [regex]::Matches($content, $secretPattern.Pattern)
    foreach ($match in $matches) {
      if (Test-KnownFalsePositive $match.Value) {
        continue
      }
      $secretHits += "$(Get-ReleaseRelativePath $file.FullName) [$($secretPattern.Name)]"
    }
  }
}

if ($secretHits.Count -gt 0) {
  Fail "Potential secret material found in release candidate: $($secretHits -join '; ')"
}
Pass "no common API key, GitHub token, access token, or cookie value patterns found in text candidate files"

Write-Host "[release-candidate] verification passed for version $ExpectedVersion in $ReleaseDir"
