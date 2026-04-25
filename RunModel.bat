@echo off
powershell.exe -ExecutionPolicy Bypass -NoExit -Command ^
    "cd 'D:\Custom API endpoint'; " ^
    ".\llama.cpp\llama-server.exe --model .\Qwen3-VL-8B-Instruct-Q8_0.gguf --mmproj .\mmproj-q8-qwen3vl8b.gguf --flash-attn on --threads 6 --ctx-size 8192 --host 0.0.0.0 --port 8002 --parallel 1 --cache-ram 512 -ctk q8_0 -ctv q8_0 --threads-batch 12 --no-mmap; "