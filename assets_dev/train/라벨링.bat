@echo off
cd /d %~dp0
call C:\Users\admin\miniconda3\condabin\conda.bat run -n sugartrain --no-capture-output python label_tool.py
pause
