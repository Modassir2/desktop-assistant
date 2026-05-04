@echo off
powershell.exe -ExecutionPolicy Bypass -NoExit -Command ^
    "cd 'D:\Custom API endpoint'; " ^
    ".\llama.cpp-b8931\llama-server.exe --model .\gemma-4-26B-A4B-it-UD-IQ4_NL.gguf --mmproj .\mmproj-Q8_0-gemma-4.gguf --flash-attn on --threads 8 --ctx-size 8192 --host 0.0.0.0 --port 8002 --parallel 1 --cache-ram 512 -ctv q8_0 -ctk q8_0; "