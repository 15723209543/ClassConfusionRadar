@echo off
REM 本文件的作用是：构建并打包项目的可运行发布版本。
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\scripts\build_exe.ps1"
if errorlevel 1 (
  echo.
  echo Build failed. Please read the message above.
  pause
)
