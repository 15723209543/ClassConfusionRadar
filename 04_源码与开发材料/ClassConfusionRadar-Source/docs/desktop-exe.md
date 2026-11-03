# Windows EXE 使用说明

这是一个面向演示的桌面启动版。

## 如何使用

1. 解压压缩包
2. 双击 `ClassConfusionRadar.exe`
3. 稍等几秒，浏览器会自动打开系统首页

首次启动时，程序会自动：

- 在本地创建 SQLite 数据库
- 自动导入内置的 `competition-demo`
- 自动导入内置的 `public-demo`
- 自动打开浏览器

## 默认访问地址

- 首页：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`

## 适用说明

- 不需要单独安装 Python
- 不需要单独安装 Node.js
- 不需要 Docker Desktop
- 默认使用本地 SQLite 和内置 demo 数据

## 如果端口 8000 被占用

可以在命令行中设置环境变量后再启动：

```powershell
$env:CCR_PORT="8010"
.\ClassConfusionRadar.exe
```
