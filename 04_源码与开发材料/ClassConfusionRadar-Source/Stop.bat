@echo off
REM 本文件的作用是：停止项目启动的本地服务进程。
setlocal
cd /d "%~dp0"

set "PS_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
set "BUNDLE_SCRIPT=scripts\bundle_stop.ps1"
set "BUNDLE_ARCHIVE=images\class-confusion-radar-demo-images.tar"
set "DEV_SCRIPT=scripts\demo_stop.ps1"

if not exist "%PS_EXE%" (
  echo PowerShell was not found on this Windows device.
  echo.
  pause
  exit /b 1
)

set "TARGET_SCRIPT="

if exist "%BUNDLE_SCRIPT%" if exist "%BUNDLE_ARCHIVE%" (
  set "TARGET_SCRIPT=%BUNDLE_SCRIPT%"
) else if exist "%DEV_SCRIPT%" (
  set "TARGET_SCRIPT=%DEV_SCRIPT%"
) else if exist "%BUNDLE_SCRIPT%" (
  echo Missing offline image archive: %BUNDLE_ARCHIVE%
  echo Please make sure the release zip was fully extracted before running Stop.bat.
  echo.
  pause
  exit /b 1
)

if not defined TARGET_SCRIPT (
  echo Missing stop script.
  echo Expected either:
  echo   - %BUNDLE_SCRIPT% with %BUNDLE_ARCHIVE%
  echo   - or %DEV_SCRIPT%
  echo Please make sure the zip archive was fully extracted.
  echo.
  pause
  exit /b 1
)

"%PS_EXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0%TARGET_SCRIPT%"
if errorlevel 1 (
  echo.
  echo Shutdown failed. Please read the message above and try again.
  echo.
  pause
  exit /b 1
)

exit /b 0
