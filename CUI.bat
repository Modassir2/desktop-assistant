@echo off
powershell.exe -ExecutionPolicy Bypass -NoExit -Command ^
    "cd 'C:\Users\Modassir\Projects\Desktop Assistant'; " ^
    ".\.venv\Scripts\Activate.ps1; " ^
    "python run.py"