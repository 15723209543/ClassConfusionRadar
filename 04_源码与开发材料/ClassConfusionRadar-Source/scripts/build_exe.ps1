# 本文件的作用是：构建并打包项目的可运行发布版本。
param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$buildVenvDir = Join-Path $env:TEMP "class-confusion-radar-build-venv"
$buildPython = Join-Path $buildVenvDir "Scripts\\python.exe"
$releaseDir = Join-Path $root "release-exe"
$packageDir = Join-Path $releaseDir "ClassConfusionRadar-Exe"
$distExe = Join-Path $root "dist\\ClassConfusionRadar.exe"
$readmeSource = Join-Path $root "docs\\desktop-exe.md"

function Write-Step([string]$text) {
    Write-Host "==> $text" -ForegroundColor Cyan
}

function Ensure-Command([string]$command, [string]$hint) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw $hint
    }
}

function Invoke-Native([string]$filePath, [string[]]$arguments) {
    & $filePath @arguments
    if ($LASTEXITCODE -ne 0) {
        $joinedArgs = $arguments -join " "
        throw "Command failed with exit code ${LASTEXITCODE}: $filePath $joinedArgs"
    }
}

function Test-BuildPythonReady([string]$pythonPath) {
    if (-not (Test-Path $pythonPath)) {
        return $false
    }

    & $pythonPath -m pip --version *> $null
    return $LASTEXITCODE -eq 0
}

Write-Step "Checking local build tools"
Ensure-Command $PythonExe "Python is not installed or is not available in PATH."
Ensure-Command "npm" "npm is not installed or is not available in PATH."

Write-Step "Building frontend static files"
Push-Location (Join-Path $root "frontend")
if (-not (Test-Path "node_modules")) {
    Invoke-Native "npm" @("install")
}
Invoke-Native "npm" @("run", "build")
Pop-Location

Write-Step "Preparing isolated build virtual environment"
if (-not (Test-BuildPythonReady $buildPython)) {
    if (Test-Path $buildVenvDir) {
        Remove-Item -LiteralPath $buildVenvDir -Recurse -Force
    }
    Invoke-Native $PythonExe @("-m", "venv", $buildVenvDir)
}

Write-Step "Installing backend runtime and PyInstaller"
Invoke-Native $buildPython @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")
Invoke-Native $buildPython @("-m", "pip", "install", "--prefer-binary", "greenlet>=3.1,<3.2")
Invoke-Native $buildPython @("-m", "pip", "install", "--prefer-binary", "-e", (Join-Path $root "backend"))
Invoke-Native $buildPython @("-m", "pip", "install", "pyinstaller>=6.11,<7")

Write-Step "Building Windows desktop executable"
Push-Location $root
Invoke-Native $buildPython @("-m", "PyInstaller", "--clean", "--noconfirm", "ClassConfusionRadar.spec")
Pop-Location

if (-not (Test-Path $distExe)) {
    throw "Build output was not created: $distExe"
}

Write-Step "Assembling portable package"
if (Test-Path $packageDir) {
    Remove-Item -LiteralPath $packageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $packageDir -Force | Out-Null
Copy-Item -LiteralPath $distExe -Destination (Join-Path $packageDir "ClassConfusionRadar.exe") -Force
if (Test-Path $readmeSource) {
    Copy-Item -LiteralPath $readmeSource -Destination (Join-Path $packageDir "README.md") -Force
}
$startGuide = Join-Path $root "操作说明_iCAN版.txt"
if (Test-Path $startGuide) {
    Copy-Item -LiteralPath $startGuide -Destination (Join-Path $packageDir "启动说明.txt") -Force
}

Write-Step "Packaging zip"
if (-not (Test-Path $releaseDir)) {
    New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
}
$zipPath = Join-Path $releaseDir "ClassConfusionRadar-Exe.zip"
if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $zipPath

Write-Host ""
Write-Host "Build finished." -ForegroundColor Green
Write-Host "Folder: $packageDir"
Write-Host "Zip:    $zipPath"
