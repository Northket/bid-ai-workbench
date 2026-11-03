@echo off
chcp 65001 >nul
title 深圳建设工程投标 AI 工作台 - 一键启动
cd /d "%~dp0"

echo ============================================
echo   深圳建设工程投标 AI 工作台 - 一键启动
echo ============================================
echo.

REM ---- 1. 后端环境检查 ----
if not exist "backend\venv\Scripts\python.exe" (
    echo [1/4] 首次运行：创建 Python 虚拟环境...
    python -m venv backend\venv
    backend\venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt
) else (
    echo [1/4] Python 环境已就绪
)

REM ---- 2. 前端依赖检查 ----
if not exist "frontend\node_modules" (
    echo [2/4] 首次运行：安装前端依赖（可能需要几分钟）...
    cd frontend
    call npm install --no-audit --no-fund
    cd ..
) else (
    echo [2/4] 前端依赖已就绪
)

REM ---- 3. 构建前端（如缺失）----
if not exist "frontend\dist\index.html" (
    echo [3/4] 构建前端页面...
    cd frontend
    call npm run build
    cd ..
) else (
    echo [3/4] 前端构建已就绪
)

REM ---- 4. 启动服务 ----
echo [4/4] 启动后端服务（同时托管前端页面）...
echo.
echo   启动后请访问:  http://localhost:8000
echo   关闭本窗口即停止服务
echo.
start "" http://localhost:8000
cd backend
venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
