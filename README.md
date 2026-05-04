# 💻 Desktop Assistant Agent

A lightweight, terminal-based (TUI) desktop assistant designed for speed and efficiency. It features a beautifully formatted command-line interface and runs completely locally using LM Studio.

### ✨ Key Features
* 📟 **Rich Terminal UI:** Clean, pretty-printed console output for easy reading and structured data display.
* 🏠 **100% Local AI Support:** Tested and optimized in local OpenAI endpoints (LM Studio, ollama, llama.cpp/llama-server.exe).
* ⌨️ **Keyboard Driven:** Quick text-based commands without leaving your terminal environment.
* ⚡ **Lightweight:** No heavy GUI overhead, running directly in your shell with minimal system usage.

### 🚀 Getting Started

#### Model Selection
* For Local LLM:
  There are many open source LLMs that can be used. While selecting a LLM for this assistant look for its UI Grounding benchmarks (like screenspot, osworld) to be 75%+ for best results
  If your own a low end harware then the best model for you is the `Qwen3vl 8b` with Q8_0 quantization. Get a Q8_0 quantized mmproj (from Hugginface `prithivMLmods/Qwen3-VL-8B-Instruct-abliterated-v2-GGUF`). Then get `ggml-org/llama.cpp` release best for your GPU or mac. Run the following code in terminal in the folder with llama.cpp, Qwen3vl 8b Q8_0 and mmproj Q8_0 file-
  ```bash
  .\llama.cpp\llama-server.exe --model .\Qwen3-VL-8B-Instruct-Q8_0.gguf --mmproj .\mmproj-q8-qwen3vl8b.gguf --ctx-size 8192 --host 0.0.0.0 --port 8002 --parallel 1 --cache-ram 1024 -ctk q8_0 -ctv q8_0 --no-mmap
  ```
  Note: Add `--flash-attn on` if you have nvidia GPU for better performance
  Now the local server will be running at "http://127.0.0.1:8002" and requires no api key.

* For Cloud LLM:
  This has been tested to work on the lowest 8b parameter model, thus almost all closed source AI models will work given that it supports images and tool calling/agentic tasks.

#### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/Modassir2/desktop-assistant
   cd desktop-assistant
   ```
   
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   
3. Setup config.json:
   Open `config.json`
   All the settings are obvious but here are the explanations anyway-
   * `base_url`
     This sets the base url to look for the OpenAI endpoint, some examples are:
     Google Gemini (via AI Studio): "https://generativelanguage.googleapis.com/v1beta/openai/"
     - LM Studio: "http://localhost:1234/v1" (or the configured port)
     - Groq: "https://api.groq.com/openai/v1"
     - OpenRouter: "https://openrouter.ai/api/v1"
     - xAI (Grok): "https://api.x.ai/v1"
     - Ollama: "http://localhost:11434/v1"
     - OpenAI: Leave empty "" or "https://api.openai.com/v1"
   * `api_key`
     Set the api key for paid AI platforms. For local LLMs usually out any placeholder text as it is not used.
   * `image_tokens`
     Sets how many tokens the AI uses to see/process a single image.This is used to calculate and turnacate the history as it grows more than `max_tokens` .
     You can ignore and leave to default 1105.
   * `max_tokens`
     Set The context limit supported by your api endpoint. At least 8192 tokens is recommended and is what I used to test it.
   * `last_n_images`
     The more the number of images, the more the processing time, especially for local LLMs, this this setting allows how many last n images can the AI see in history.
     Recommnded at least 3. Keep a very large number to set it to infinity (Not-recommnded).
   * `width`
     The width of your monitor's resolution, used to calculate the x coordinates to click at from the AI output.
   * `height`
     The height of your monitor's resolution, used to calculate the y coordinate to click at from the AI ouutput.
   * `dev_mode`
     This currently does nothing. Just ignore this
   * `monitor`
     If your own more than one monitor setup, then set the monitor number that the AI will see. The monitor number can be seen in windows+I (Open settings) > System > Display
     Then click on the "Identify" button. The number shown on each monitor is the monitor's number.
     
5. Run the assistant:
   Now finally-
   ```bash
   python run.py
   ```

### 🛠️ Tech Stack
* **Language:** Python
* **Libraries used for Pretty Printing:** textual, rich, colorma

### 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Created by Modassir
<3
