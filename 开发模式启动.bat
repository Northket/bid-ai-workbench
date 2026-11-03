@echo off
chcp 65001 >nul
title 投标AI工作台 - 开发模式（前后端分离热更新）
cd /d "%~dp0"

echo ============================================
echo   开发模式启动（代码修改实时生效）
echo   后端: http://localhost:8000  （API 文档 /docs）
echo   前端: http://localhost:5173  （开发入口）
echo ============================================
echo.

if not exist "backend\venv\Scripts\python.exe" (
    echo 首次运行：创建 Python 虚拟环境...
    python -m venv backend\venv
    backend\venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt
)
if not exist "frontend\node_modules" (
    echo 首次运行：安装前端依赖...
    cd frontend && call npm install --no-audit --no-fund && cd ..
)

echo 启动后端（热重载）...
start "后端-FastAPI" cmd /k "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000"

timeout /t 2 /nobreak >nul

echo 启动前端（Vite 开发服务器）...
start "前端-Vite" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 4 /nobreak >nul
start "" http://localhost:5173
echo.
echo 两个窗口均已启动，关闭对应窗口即停止对应服务。
pause
