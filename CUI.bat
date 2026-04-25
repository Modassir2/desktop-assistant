@echo off
powershell.exe -ExecutionPolicy Bypass -NoExit -Command ^
    "cd 'C:\Users\Modassir\Projects\Infinity v2'; " ^
    ".\.venv\Scripts\Activate.ps1; " ^
    "python run.py"