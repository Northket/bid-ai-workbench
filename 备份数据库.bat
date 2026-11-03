@echo off
chcp 65001 >nul
title 数据库备份 - 深圳建设工程投标 AI 工作台
cd /d "%~dp0backend"

echo 正在备份数据库与上传文件到 backend\backups\ ...
venv\Scripts\python.exe scripts\backup_db.py
if errorlevel 1 (
    echo 备份失败，请检查 backend\venv 是否存在。
) else (
    echo.
    echo 备份完成。恢复方法见备份目录内 MANIFEST.txt。
)
pause
