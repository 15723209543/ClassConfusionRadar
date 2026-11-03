# 本文件的作用是：启动项目运行所需的本地服务。
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Write-Step {
  param([string]$Message)
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Fail-Start {
  param([string]$Message)
  throw [System.Exception]::new($Message)
}

function Ensure-EnvFile {
  param(
    [string]$TargetPath,
    [string]$ExamplePath
  )

  if (-not (Test-Path $ExamplePath)) {
    Fail-Start "Missing example config file: $ExamplePath"
  }

  if (-not (Test-Path $TargetPath)) {
    Copy-Item $ExamplePath $TargetPath
    Write-Host "Created env file: $TargetPath"
  }
}

function Ensure-Command {
  param(
    [string]$CommandName,
    [string]$FriendlyMessage
  )

  if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
    Fail-Start $FriendlyMessage
  }
}

function Resolve-PythonInvocation {
  $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
  if ($pythonCommand) {
    return @{
      FilePath   = $pythonCommand.Source
      PrefixArgs = @()
    }
  }

  $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($pyLauncher) {
    return @{
      FilePath   = $pyLauncher.Source
      PrefixArgs = @("-3")
    }
  }

  Fail-Start "Python 3.9+ was not found. Please install Python and try again."
}

function Get-EnvValue {
  param(
    [string]$FilePath,
    [string]$Key,
    [string]$DefaultValue
  )

  if (-not (Test-Path $FilePath)) {
    return $DefaultValue
  }

  $line = Get-Content -Path $FilePath -Encoding utf8 | Where-Object {
    $_ -match "^\s*$Key=(.+)$"
  } | Select-Object -First 1

  if (-not $line) {
    return $DefaultValue
  }

  return ($line -replace "^\s*$Key=", "").Trim()
}

function Ensure-DockerReady {
  Write-Step "Checking Docker Desktop"
  Ensure-Command -CommandName "docker" -FriendlyMessage "Docker was not found. Please install Docker Desktop and try again."

  cmd /c "docker compose version >nul 2>nul" | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Fail-Start "Docker is installed but docker compose is unavailable. Please reinstall or repair Docker Desktop."
  }

  cmd /c "docker info >nul 2>nul" | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Fail-Start "Docker Desktop is not running. Please start Docker Desktop and try again."
  }
}

function Start-DemoStack {
  Write-Step "Starting Docker Compose"
  $composeText = ""
  $logPath = Join-Path $env:TEMP ("class-confusion-radar-compose-{0}.log" -f ([guid]::NewGuid().ToString("N")))

  for ($attempt = 1; $attempt -le 2; $attempt++) {
    if ($attempt -gt 1) {
      Write-Host "Retrying Docker Compose after a short wait..." -ForegroundColor Yellow
      Start-Sleep -Seconds 5
    }

    if (Test-Path $logPath) {
      Remove-Item $logPath -Force -ErrorAction SilentlyContinue
    }

    cmd /c "set BUILDKIT_PROGRESS=plain&& docker compose up --build -d > `"$logPath`" 2>&1"
    if (Test-Path $logPath) {
      $composeText = Get-Content -Path $logPath -Raw -Encoding utf8
      if ($composeText) {
        $composeText.TrimEnd().Split([Environment]::NewLine) | ForEach-Object { Write-Host $_ }
      }
    } else {
      $composeText = ""
    }

    if ($LASTEXITCODE -eq 0) {
      return
    }
  }

  if ($composeText -match "port is already allocated|Ports are not available|address already in use|bind") {
    Fail-Start "Port 5432, 8000, or 5173 is already in use. Please close the conflicting program and try again."
  }

  if ($composeText -match "auth\.docker\.io/token|failed to fetch oauth token|failed to authorize|load metadata for docker\.io/library") {
    Fail-Start "Docker could not download the required base images from Docker Hub. Please check your network, proxy, or Docker registry access, then run Run.bat again."
  }

  if ($composeText -match "pull access denied|repository does not exist") {
    Fail-Start "Docker could not pull one of the required images. Please check Docker registry access and try again."
  }

  Fail-Start "Docker Compose failed to start. Please confirm Docker Desktop is running and try again."
}

function Wait-ServiceReady {
  param(
    [string]$ServiceName,
    [string]$Url,
    [datetime]$Deadline
  )

  while ((Get-Date) -lt $Deadline) {
    try {
      $response = Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 3
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
        return
      }
    } catch {}

    Start-Sleep -Seconds 2
  }

  Fail-Start "$ServiceName was not ready in time. Please run docker compose logs and inspect the startup logs."
}

function Seed-DemoData {
  param(
    [string]$BackendUrl,
    [string]$FrontendUrl
  )

  Write-Step "Preparing demo data"
  $python = Resolve-PythonInvocation
  $seedArgs = @(
    $python.PrefixArgs +
    @(
      "scripts/demo_seed.py",
      "--base-url", $BackendUrl,
      "--frontend-url", $FrontendUrl
    )
  )

  & $python.FilePath @seedArgs
  if ($LASTEXITCODE -ne 0) {
    Fail-Start "Demo data preparation failed. Please try again."
  }
}

try {
  Ensure-EnvFile -TargetPath ".env" -ExamplePath ".env.example"
  Ensure-EnvFile -TargetPath "backend/.env" -ExamplePath "backend/.env.example"
  Ensure-EnvFile -TargetPath "frontend/.env" -ExamplePath "frontend/.env.example"
  Ensure-DockerReady

  $envFilePath = Join-Path $root ".env"
  $backendPort = Get-EnvValue -FilePath $envFilePath -Key "BACKEND_PORT" -DefaultValue "8000"
  $frontendPort = Get-EnvValue -FilePath $envFilePath -Key "FRONTEND_PORT" -DefaultValue "5173"
  $backendUrl = "http://127.0.0.1:$backendPort"
  $frontendUrl = "http://127.0.0.1:$frontendPort"

  Start-DemoStack

  Write-Step "Waiting for services to become ready"
  $deadline = (Get-Date).AddMinutes(5)
  Wait-ServiceReady -ServiceName "Backend service" -Url "$backendUrl/health" -Deadline $deadline
  Wait-ServiceReady -ServiceName "Frontend service" -Url $frontendUrl -Deadline $deadline

  Seed-DemoData -BackendUrl $backendUrl -FrontendUrl $frontendUrl

  Write-Step "Opening the frontend homepage"
  Start-Process $frontendUrl

  Write-Host ""
  Write-Host "Demo environment is ready." -ForegroundColor Green
  Write-Host "Frontend: $frontendUrl"
  Write-Host "Backend docs: $backendUrl/docs"
  Write-Host "Suggested flow: open the demo session -> run analytics -> inspect a high-risk segment -> generate suggestions"
  exit 0
}
catch {
  Write-Host ""
  Write-Host "Startup failed: " -ForegroundColor Red -NoNewline
  Write-Host $_.Exception.Message -ForegroundColor Red
  Write-Host "Please fix the issue above, then double-click Run.bat again." -ForegroundColor Yellow
  exit 1
}
