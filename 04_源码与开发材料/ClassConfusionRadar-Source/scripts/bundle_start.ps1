# 本文件的作用是：启动项目运行所需的本地服务。
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$composeFile = Join-Path $root "docker-compose.bundle.yml"
$imageArchive = Join-Path $root "images\class-confusion-radar-demo-images.tar"
$requiredImages = @(
  "class-confusion-radar-backend:demo",
  "class-confusion-radar-frontend:demo",
  "postgres:15-alpine"
)

function Write-Step {
  param([string]$Message)
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Fail-Start {
  param([string]$Message)
  throw [System.Exception]::new($Message)
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

function Ensure-ReleaseFiles {
  if (-not (Test-Path $composeFile)) {
    Fail-Start "Missing bundle compose file: docker-compose.bundle.yml"
  }

  if (-not (Test-Path $imageArchive)) {
    Fail-Start "Missing offline image archive: images\\class-confusion-radar-demo-images.tar"
  }
}

function Test-ImageExists {
  param([string]$ImageTag)
  cmd /c "docker image inspect $ImageTag >nul 2>nul" | Out-Null
  return $LASTEXITCODE -eq 0
}

function Ensure-ImageArchiveLoaded {
  $missingImages = @($requiredImages | Where-Object { -not (Test-ImageExists $_) })
  if ($missingImages.Count -eq 0) {
    return
  }

  Write-Step "Importing offline Docker images"
  $loadOutput = & docker load -i $imageArchive 2>&1
  if ($loadOutput) {
    $loadOutput | ForEach-Object { Write-Host $_ }
  }

  if ($LASTEXITCODE -ne 0) {
    Fail-Start "Failed to import the offline Docker images. Please make sure the image archive is complete and try again."
  }

  $stillMissing = @($requiredImages | Where-Object { -not (Test-ImageExists $_) })
  if ($stillMissing.Count -gt 0) {
    Fail-Start "The offline image archive was loaded, but some required images are still missing. Please rebuild the release package."
  }
}

function Start-BundleStack {
  Write-Step "Starting bundled Docker services"
  $logPath = Join-Path $env:TEMP ("class-confusion-radar-bundle-{0}.log" -f ([guid]::NewGuid().ToString("N")))
  $composeText = ""

  for ($attempt = 1; $attempt -le 2; $attempt++) {
    if ($attempt -gt 1) {
      Write-Host "Retrying bundled Docker startup after a short wait..." -ForegroundColor Yellow
      Start-Sleep -Seconds 5
    }

    if (Test-Path $logPath) {
      Remove-Item $logPath -Force -ErrorAction SilentlyContinue
    }

    cmd /c "set BUILDKIT_PROGRESS=plain&& docker compose -f `"$composeFile`" up -d > `"$logPath`" 2>&1"
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

  Fail-Start "Bundled Docker services failed to start. Please inspect the compose output above and try again."
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

  Fail-Start "$ServiceName was not ready in time. Please inspect the docker compose logs and try again."
}

function Seed-DemoData {
  param(
    [string]$BackendUrl,
    [string]$FrontendUrl
  )

  Write-Step "Preparing demo data"
  $seedOutput = & docker compose -f $composeFile exec -T backend python scripts/demo_seed.py --base-url $BackendUrl --frontend-url $FrontendUrl 2>&1
  if ($seedOutput) {
    $seedOutput | ForEach-Object { Write-Host $_ }
  }

  if ($LASTEXITCODE -ne 0) {
    Fail-Start "Demo data preparation failed inside the backend container. Please inspect the output above and try again."
  }
}

try {
  Ensure-DockerReady
  Ensure-ReleaseFiles
  Ensure-ImageArchiveLoaded
  Start-BundleStack

  $backendUrl = "http://127.0.0.1:8000"
  $frontendUrl = "http://127.0.0.1:5173"

  Write-Step "Waiting for services to become ready"
  $deadline = (Get-Date).AddMinutes(5)
  Wait-ServiceReady -ServiceName "Backend service" -Url "$backendUrl/health" -Deadline $deadline
  Wait-ServiceReady -ServiceName "Frontend service" -Url $frontendUrl -Deadline $deadline

  Seed-DemoData -BackendUrl $backendUrl -FrontendUrl $frontendUrl

  Write-Step "Opening the frontend homepage"
  Start-Process $frontendUrl

  Write-Host ""
  Write-Host "Demo bundle is ready." -ForegroundColor Green
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
