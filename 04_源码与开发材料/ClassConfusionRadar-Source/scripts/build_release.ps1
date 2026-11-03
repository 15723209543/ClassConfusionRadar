# 本文件的作用是：构建并打包项目的可运行发布版本。
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$releaseName = "ClassConfusionRadar-Demo"
$releaseBase = Join-Path $root "release"
$releaseDir = Join-Path $releaseBase $releaseName
$zipPath = Join-Path $releaseBase "$releaseName.zip"
$imageDir = Join-Path $releaseDir "images"
$imageArchive = Join-Path $imageDir "class-confusion-radar-demo-images.tar"
$bundleFiles = @(
  "Run.bat",
  "Stop.bat",
  "docker-compose.bundle.yml",
  "README.md"
)

function Write-Step {
  param([string]$Message)
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Fail-Build {
  param([string]$Message)
  throw [System.Exception]::new($Message)
}

function Ensure-Command {
  param(
    [string]$CommandName,
    [string]$FriendlyMessage
  )

  if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
    Fail-Build $FriendlyMessage
  }
}

function Ensure-DockerReady {
  Write-Step "Checking Docker Desktop"
  Ensure-Command -CommandName "docker" -FriendlyMessage "Docker was not found. Please install Docker Desktop and try again."

  cmd /c "docker compose version >nul 2>nul" | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Fail-Build "Docker is installed but docker compose is unavailable. Please reinstall or repair Docker Desktop."
  }

  cmd /c "docker info >nul 2>nul" | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Fail-Build "Docker Desktop is not running. Please start Docker Desktop and try again."
  }
}

function Invoke-DockerBuildCommand {
  param(
    [string]$FriendlyTargetName,
    [string]$CommandText
  )

  $logPath = Join-Path $env:TEMP ("class-confusion-radar-release-{0}.log" -f ([guid]::NewGuid().ToString("N")))
  $buildText = ""

  if (Test-Path $logPath) {
    Remove-Item $logPath -Force -ErrorAction SilentlyContinue
  }

  cmd /c "set BUILDKIT_PROGRESS=plain&& $CommandText > `"$logPath`" 2>&1"
  if (Test-Path $logPath) {
    $buildText = Get-Content -Path $logPath -Raw -Encoding utf8
    if ($buildText) {
      $buildText.TrimEnd().Split([Environment]::NewLine) | ForEach-Object { Write-Host $_ }
    }
  }

  if ($LASTEXITCODE -eq 0) {
    return
  }

  if ($buildText -match "auth\.docker\.io/token|failed to fetch oauth token|pull access denied|requested access to the resource is denied|not found") {
    Fail-Build "Docker could not download the base image required for the $FriendlyTargetName release image. Please check Docker Hub access or your registry mirror, then try again."
  }

  Fail-Build "Failed to build the $FriendlyTargetName release image."
}

function Build-ReleaseImages {
  Write-Step "Ensuring the PostgreSQL base image is available"
  & docker pull postgres:15-alpine
  if ($LASTEXITCODE -ne 0) {
    Fail-Build "Failed to pull postgres:15-alpine. Please check Docker registry access and try again."
  }

  Write-Step "Building the backend release image"
  Invoke-DockerBuildCommand `
    -FriendlyTargetName "backend" `
    -CommandText "docker build -f backend/Dockerfile.release -t class-confusion-radar-backend:demo ."

  Write-Step "Building the frontend release image"
  Invoke-DockerBuildCommand `
    -FriendlyTargetName "frontend" `
    -CommandText "docker build -f frontend/Dockerfile.release --build-arg VITE_API_BASE_URL=http://127.0.0.1:8000 -t class-confusion-radar-frontend:demo frontend"
}

function Prepare-ReleaseDirectory {
  Write-Step "Preparing the release directory"

  if (Test-Path $releaseDir) {
    Remove-Item $releaseDir -Recurse -Force
  }
  if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
  }

  New-Item -ItemType Directory -Path $releaseDir | Out-Null
  New-Item -ItemType Directory -Path $imageDir | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $releaseDir "scripts") | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $releaseDir "infra\postgres") -Force | Out-Null
}

function Copy-ReleaseAssets {
  Write-Step "Copying the release assets"

  foreach ($file in $bundleFiles) {
    Copy-Item -Path (Join-Path $root $file) -Destination (Join-Path $releaseDir $file) -Force
  }

  Copy-Item -Path (Join-Path $root "scripts\bundle_start.ps1") -Destination (Join-Path $releaseDir "scripts\bundle_start.ps1") -Force
  Copy-Item -Path (Join-Path $root "scripts\bundle_stop.ps1") -Destination (Join-Path $releaseDir "scripts\bundle_stop.ps1") -Force
  Copy-Item -Path (Join-Path $root "infra\postgres\init.sql") -Destination (Join-Path $releaseDir "infra\postgres\init.sql") -Force
}

function Export-ReleaseImages {
  Write-Step "Exporting offline Docker images"
  & docker image save class-confusion-radar-backend:demo class-confusion-radar-frontend:demo postgres:15-alpine -o $imageArchive
  if ($LASTEXITCODE -ne 0) {
    Fail-Build "Failed to export the offline Docker image archive."
  }
}

function New-ReleaseZip {
  Write-Step "Creating the release zip"

  $tarCommand = Get-Command tar.exe -ErrorAction SilentlyContinue
  if ($tarCommand) {
    Push-Location $releaseBase
    try {
      & $tarCommand.Source -a -cf $zipPath $releaseName
      if ($LASTEXITCODE -ne 0) {
        Fail-Build "Failed to create the release zip with tar.exe."
      }
    }
    finally {
      Pop-Location
    }
    return
  }

  Compress-Archive -Path (Join-Path $releaseDir "*") -DestinationPath $zipPath -Force
}

try {
  Ensure-DockerReady
  Build-ReleaseImages
  Prepare-ReleaseDirectory
  Copy-ReleaseAssets
  Export-ReleaseImages
  New-ReleaseZip

  Write-Host ""
  Write-Host "Release bundle is ready." -ForegroundColor Green
  Write-Host "Folder: $releaseDir"
  Write-Host "Zip: $zipPath"
  Write-Host "Send the zip file to the target Windows device, then ask the recipient to start Docker Desktop and double-click Run.bat."
  exit 0
}
catch {
  Write-Host ""
  Write-Host "Release build failed: " -ForegroundColor Red -NoNewline
  Write-Host $_.Exception.Message -ForegroundColor Red
  exit 1
}
