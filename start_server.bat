@echo off
title EcoTrack Server
echo.
echo ========================================
echo   EcoTrack - Starting Local Server...
echo ========================================
echo.
cd /d "%~dp0"
python server.py
pause
