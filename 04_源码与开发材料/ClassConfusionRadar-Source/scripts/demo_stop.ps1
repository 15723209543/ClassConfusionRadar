# 本文件的作用是：停止项目启动的本地服务进程。
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Fail-Stop {
  param([string]$Message)
  throw [System.Exception]::new($Message)
}

function Ensure-Command {
  param(
    [string]$CommandName,
    [string]$FriendlyMessage
  )

  if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
    Fail-Stop $FriendlyMessage
  }
}

try {
  Ensure-Command -CommandName "docker" -FriendlyMessage "Docker was not found. Please install Docker Desktop and try again."

  cmd /c "docker compose version >nul 2>nul" | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Fail-Stop "Docker is installed but docker compose is unavailable. Please reinstall or repair Docker Desktop."
  }

  cmd /c "docker info >nul 2>nul" | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Fail-Stop "Docker Desktop is not running. Please start Docker Desktop and try again."
  }

  Write-Host "==> Stopping Docker Compose services" -ForegroundColor Cyan
  $composeOutput = & docker compose down 2>&1
  if ($composeOutput) {
    $composeOutput | ForEach-Object { Write-Host $_ }
  }

  if ($LASTEXITCODE -ne 0) {
    Fail-Stop "Failed to stop the services. Please run docker compose down manually and inspect the output."
  }

  Write-Host ""
  Write-Host "Demo services were stopped." -ForegroundColor Green
  exit 0
}
catch {
  Write-Host ""
  Write-Host "Shutdown failed: " -ForegroundColor Red -NoNewline
  Write-Host $_.Exception.Message -ForegroundColor Red
  Write-Host "Please fix the issue above, then double-click Stop.bat again." -ForegroundColor Yellow
  exit 1
}
