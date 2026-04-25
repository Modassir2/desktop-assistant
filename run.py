import json
import colorama
import utils
from functions import *

colorama.init(autoreset=True)

GREY = colorama.Fore.LIGHTBLACK_EX
CYAN = colorama.Fore.CYAN
GREEN = colorama.Fore.GREEN
LIGHTGREEEN = colorama.Fore.LIGHTGREEN_EX
RED = colorama.Fore.LIGHTRED_EX
#BLUE = colorama.Fore.BLUE
YELLOW = colorama.Fore.YELLOW
RESET = colorama.Fore.RESET

def clear_line():
    print("\033[2K\033[1G", end="")

if __name__ == "__main__":
    print(f"{YELLOW}Commands:\n/exit - Exit Program\n/clear - Clear context{RESET}\n")
    while True:
        if user_turn == True:
            try:
                prompt = input(f"{RED}You: {RESET}")
                assistant_printed=False
            except (KeyboardInterrupt, EOFError):
                print(f"\n{YELLOW}[Interrupted] Type '/exit' or '/bye' to exit.{RESET}")
                continue
            if prompt[0]=='/':
                if prompt.lower() == "/exit":
                    print(f"{YELLOW}Exiting...{RESET}")
                    break
                elif prompt.lower()=="/clear":
                    history=utils.new_history()
                    utils.save_history(history)
                    print(f"{YELLOW}Cleared Context{RESET}")
                    continue
                else:
                    print(f"\n{YELLOW}[Command] Invalid command!{RESET}")
                    continue
            
            if prompt.strip():
                history.append({"role": "user", "content": prompt})
            else:
                print(f"{YELLOW}Empty Prompt!{RESET}")
        
        if not assistant_printed:
            print(f"{RED}Assistant:{RESET}\n", end="", flush=True)
            assistant_printed=True
        full_content = ""
        full_reasoning = ""
        tool_calls_buffer = {}
        current_tool_call = None
        content_printed = False
        reasoning_printed = False
        removed_processing=False
        thinking_start_time = None
        utils.save_history(history)
        
        try:
            print(f"{YELLOW}Processing...{RESET}",end="")
            response = client.chat.completions.create(
                messages=history,
                tools=tools,
                model=model,
                stream=True,
            )
            
            for chunk in response:
                delta = chunk.choices[0].delta
                if not removed_processing:
                    print("\r" + " " * 15 + "\r", end="")
                    removed_processing=True
                
                if delta.content and delta.content.strip():
                    if reasoning_printed and not content_printed:
                        print(f"\r{CYAN}[Thought for {time.time() - thinking_start_time:.1f}s]{RESET}   ", end="", flush=True)
                        reasoning_printed = False
                    if not content_printed:
                        print(f"\n{LIGHTGREEEN}[Content:]{RESET}\n", end="", flush=True)
                    content_printed = True
                    print(f"{LIGHTGREEEN}{delta.content}{RESET}", end="", flush=True)
                    full_content += delta.content
                
                reasoning_content = getattr(delta, 'reasoning_content', None)
                if reasoning_content:
                    if not reasoning_printed:
                        print(f"{CYAN}[Thinking...]{RESET}", end="", flush=True)
                        reasoning_printed = True
                        thinking_start_time = time.time()
                    elapsed = time.time() - thinking_start_time
                    print(f"\r{CYAN}[Thinking...]{RESET} {elapsed:.1f}s", end="", flush=True)
                    full_reasoning += reasoning_content
                
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        if tc_delta.index is not None:
                            if tc_delta.index not in tool_calls_buffer:
                                tool_calls_buffer[tc_delta.index] = {
                                    "id": tc_delta.id or "",
                                    "function": {"name": "", "arguments": ""}
                                }
                            if tc_delta.id:
                                tool_calls_buffer[tc_delta.index]["id"] = tc_delta.id
                            if tc_delta.function:
                                if tc_delta.function.name:
                                    tool_calls_buffer[tc_delta.index]["function"]["name"] += tc_delta.function.name
                                if tc_delta.function.arguments:
                                    tool_calls_buffer[tc_delta.index]["function"]["arguments"] += tc_delta.function.arguments
        except KeyboardInterrupt:
            print(f"\n{YELLOW}[Interrupted] Stopped generating. Returning to prompt...{RESET}")
            if full_content.strip():
                history.append({"role": "assistant", "content": full_content.strip()})
            user_turn = True
            history = utils.truncate_history(history)
            history = utils.optimize_history(history)
            utils.save_history(history)
            continue

        if reasoning_printed and thinking_start_time is not None:
            elapsed = time.time() - thinking_start_time
            print(f"\r{CYAN}[Thought for {elapsed:.1f}s]{RESET}")

        print()
        
        content = full_content.strip()
        finish_reason = chunk.choices[0].finish_reason if hasattr(chunk.choices[0], 'finish_reason') else None
        
        if content and not tool_calls_buffer:
            if len(content) != 0:
                history.append({"role": "assistant", "content": content})
                user_turn = True

        if tool_calls_buffer:
            user_turn = False
            
            tool_calls_json = []
            for idx in sorted(tool_calls_buffer.keys()):
                tc_data = tool_calls_buffer[idx]
                tool_calls_json.append({
                    "id": tc_data["id"],
                    "type": "function",
                    "function": {
                        "name": tc_data["function"]["name"],
                        "arguments": tc_data["function"]["arguments"]
                    }
                })
            
            history.append({
                'role': 'assistant',
                'content': content if content else None,
                'tool_calls': tool_calls_json
            })
            utils.save_history(history)
            
            for tool_call_json in tool_calls_json:
                try:
                    func_name = tool_call_json["function"]["name"]
                    func_args = json.loads(tool_call_json["function"]["arguments"])
                    func = tool_map.get(func_name)
                    if func:
                        print(f"{GREY}[Tool Call:] {func_name}({func_args}){RESET}")
                        result = func(**func_args)
                        result[0]['tool_call_id'] = tool_call_json["id"]
                        r=result[0]['content'][0].get('text')
                        if r:
                            print(f"{GREY}[Result:] {r if len(r)<=5000 else r[:5000:]}{RESET}")
                        else:
                            print(f"{GREY}[Result:] No Text Output.{RESET}")
                        history.extend(result)
                    else:
                        history.append({'role': 'tool', 'tool_call_id': tool_call_json["id"], "content": f"Error: {func_name} does not exist."})
                except (KeyboardInterrupt, EOFError):
                    print(f"\n{YELLOW}[Interrupted:] Tool execution cancelled. Returning to prompt...{RESET}")
                    user_turn = True
                    history = utils.truncate_history(history)
                    history = utils.optimize_history(history)
                    utils.save_history(history)
                    break
        
        history=utils.update_sys_mem(history)
        history = utils.truncate_history(history)
        history = utils.optimize_history(history)
        utils.save_history(history)