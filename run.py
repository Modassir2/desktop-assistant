import json
import argparse
import sys
import time
import asyncio
from typing import Optional, List, Dict, Any, Callable

from openai import OpenAI, AsyncOpenAI
from rich.console import Console, Group
from rich.panel import Panel
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, Log, LoadingIndicator
from textual.containers import ScrollableContainer, Vertical, Horizontal, Container
from textual.binding import Binding
from textual import work, events
from textual.message import Message

import utils
from functions import *

# Initialize Rich console
console = Console()

class DesktopAssistant:
    def __init__(self):
        self.config = utils.load_config()
        self.tools = utils.load_tools()
        self.model = self.config.get("model", "gpt-4o")
        self.client = AsyncOpenAI(
            base_url=self.config.get("base_url"),
            api_key=self.config.get("api_key")
        )
        self.history = utils.load_history()
        self.history = utils.optimize_history(self.history)
        utils.save_history(self.history)

    def clear_history(self):
        self.history = utils.new_history()
        utils.save_history(self.history)

    async def process_prompt(self, prompt: str, callback: Callable[[Dict[str, Any]], Any]):
        """
        Processes a user prompt and yields status/content updates.
        """
        if prompt:
            self.history.append({"role": "user", "content": prompt})
        
        full_content = ""
        tool_calls_buffer = {}
        
        while True:
            utils.save_history(self.history)
            try:
                await callback({"status": "processing", "message": "Processing..."})
                
                response = await self.client.chat.completions.create(
                    messages=self.history,
                    tools=self.tools,
                    model=self.model,
                    stream=True,
                )
                
                await callback({"status": "start_assistant", "message": ""})
                
                async for chunk in response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    
                    # Handle reasoning content if available (some models)
                    reasoning_content = getattr(delta, 'reasoning_content', None)
                    if reasoning_content:
                        await callback({"status": "reasoning", "content": reasoning_content})

                    # Handle main content
                    if delta.content:
                        full_content += delta.content
                        await callback({"status": "content", "content": delta.content})
                    
                    # Handle tool calls
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

            except asyncio.CancelledError:
                # Handle Ctrl+C or task cancellation
                if full_content:
                    self.history.append({"role": "assistant", "content": full_content})
                    self.history = utils.update_sys_mem(self.history)
                    self.history = utils.truncate_history(self.history)
                    self.history = utils.optimize_history(self.history)
                    utils.save_history(self.history)
                await callback({"status": "interrupted", "message": "Generation interrupted."})
                raise # Re-raise to let the caller handle it if needed
            except Exception as e:
                await callback({"status": "error", "message": str(e)})
                return

            # After streaming is done
            if full_content and not tool_calls_buffer:
                self.history.append({"role": "assistant", "content": full_content})
                self.history = utils.update_sys_mem(self.history)
                self.history = utils.truncate_history(self.history)
                self.history = utils.optimize_history(self.history)
                utils.save_history(self.history)
                await callback({"status": "done", "message": "Ready"})
                return

            if tool_calls_buffer:
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
                
                self.history.append({
                    'role': 'assistant',
                    'content': full_content if full_content else None,
                    'tool_calls': tool_calls_json
                })
                
                for tool_call_json in tool_calls_json:
                    func_name = tool_call_json["function"]["name"]
                    func_args_str = tool_call_json["function"]["arguments"]
                    try:
                        func_args = json.loads(func_args_str)
                        func = tool_map.get(func_name)
                        if func:
                            await callback({"status": "tool_call", "name": func_name, "args": func_args_str})
                            result = await asyncio.to_thread(func, **func_args)
                            result[0]['tool_call_id'] = tool_call_json["id"]
                            self.history.extend(result)
                            await callback({"status": "tool_result", "name": func_name, "result": "Success"})
                        else:
                            error_msg = f"Error: {func_name} does not exist."
                            self.history.append({'role': 'tool', 'tool_call_id': tool_call_json["id"], "content": error_msg})
                            await callback({"status": "error", "message": error_msg})
                    except Exception as e:
                        error_msg = f"Error executing {func_name}: {str(e)}"
                        self.history.append({'role': 'tool', 'tool_call_id': tool_call_json["id"], "content": error_msg})
                        await callback({"status": "error", "message": error_msg})
                
                # Reset for next iteration (tool results might trigger more tools or final response)
                full_content = ""
                tool_calls_buffer = {}
                continue
            
            # If no content and no tool calls, something might be wrong or it's just finished
            await callback({"status": "done", "message": "Ready"})
            return


class ChatMessage(Static):
    """A widget to display a chat message."""
    def __init__(self, role: str, content: str, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.content = content

    def render(self) -> Panel:
        title = "You" if self.role == "user" else "Assistant"
        style = "red" if self.role == "user" else "light_green"
        return Panel(Markdown(self.content), title=title, border_style=style, expand=True)

class ToolCallMessage(Static):
    """A widget to display a tool call and its result."""
    def __init__(self, tool_name: str, tool_args: str, tool_result: str = "Pending...", **kwargs):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.tool_result = tool_result
        self.add_class("assistant")

    def render(self) -> Panel:
        content = f"**Tool:** `{self.tool_name}`\n**Args:** `{self.tool_args}`\n**Status:** {self.tool_result}"
        return Panel(Markdown(content), title="Tool Action", border_style="orange3", expand=True)

class ReasoningMessage(Static):
    """A widget to display the reasoning/thinking process with a timer."""
    def __init__(self, content: str = "", **kwargs):
        super().__init__(**kwargs)
        self.content = content
        self.start_time = time.time()
        self.elapsed_time = 0.0
        self.timer_active = True
        self.expanded = False
        self._timer = None
        self.add_class("assistant")
        self.add_class("collapsed")

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.1, self.update_timer)

    def update_timer(self) -> None:
        if self.timer_active:
            self.elapsed_time = time.time() - self.start_time
            self.refresh()

    def stop_timer(self) -> None:
        if self.timer_active:
            self.timer_active = False
            if self._timer:
                self._timer.stop()
            self.elapsed_time = time.time() - self.start_time
            self.refresh()

    def on_click(self) -> None:
        self.toggle()

    def toggle(self) -> None:
        self.expanded = not self.expanded
        if self.expanded:
            self.remove_class("collapsed")
        else:
            self.add_class("collapsed")
        self.refresh()

    def render(self) -> Panel:
        status = "Thought for" if not self.timer_active else "Thinking for"
        chevron = "▼" if self.expanded else "▶"
        header = f"{chevron} **{status} {self.elapsed_time:.1f}s...**"
        
        if self.expanded:
            full_markdown = f"{header}\n\n{self.content}" if self.content else header
        else:
            full_markdown = header
            
        return Panel(
            Markdown(full_markdown), 
            title="Reasoning", 
            border_style="cyan", 
            expand=True
        )

class CommandSuggestion(Static):
    """A single clickable command suggestion."""
    def __init__(self, command: str, description: str, **kwargs):
        super().__init__(**kwargs)
        self.command = command
        self.description = description
        self.can_focus = True

    def render(self) -> str:
        return f"[bold cyan]{self.command}[/bold cyan] - [dim]{self.description}[/dim]"

    def on_click(self) -> None:
        self.post_message(self.Selected(self.command))

    def on_key(self, event: events.Key) -> None:
        if event.key in ("enter", " "):
            self.post_message(self.Selected(self.command))

    class Selected(Message):
        """Message sent when a suggestion is selected."""
        def __init__(self, command: str):
            super().__init__()
            self.command = command

class CommandSuggestor(Vertical):
    """A container for command suggestions."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.commands = [
            ("/clear", "Clear chat history"),
            ("/exit", "Exit the application"),
            ("/help", "Show help notification")
        ]

    def on_mount(self) -> None:
        self.display = False

    def update_suggestions(self, current_input: str) -> None:
        self.query(CommandSuggestion).remove()
        
        if not current_input.startswith("/"):
            self.display = False
            return

        filtered = [
            (cmd, desc) for cmd, desc in self.commands 
            if cmd.startswith(current_input)
        ]

        if not filtered:
            self.display = False
            return

        for cmd, desc in filtered:
            self.mount(CommandSuggestion(cmd, desc))
        
        self.display = True

class DesktopAssistantApp(App):
    """A Textual app for the Desktop Assistant."""
    CSS = """
    Screen {
        background: $surface;
    }
    #chat-container {
        height: 1fr;
        overflow-y: scroll;
        padding: 1;
    }
    #input-container {
        height: auto;
        dock: bottom;
        background: $boost;
        padding: 0 1 1 1;
    }
    Input {
        background: #2a2a2a;
        border: tall gray;
        color: $text;
    }
    Input:focus {
        border: tall #888888;
    }
    CommandSuggestor {
        height: auto;
        max-height: 10;
        background: $surface;
        border: round $accent;
        margin: 0 1;
        padding: 0 1;
        display: none;
    }
    CommandSuggestion {
        padding: 0 1;
        height: 1;
        width: 1fr;
    }
    CommandSuggestion:hover {
        background: $accent;
        color: $text;
        text-style: bold;
    }
    CommandSuggestion:focus {
        background: $accent;
        color: $text;
        text-style: bold;
        border: none;
    }
    #status-bar {
        height: 1;
        background: transparent;
        color: $text;
        content-align: center middle;
        width: 1fr;
    }
    #loading-indicator {
        height: 1;
        width: 4;
        background: transparent;
        color: $accent;
    }
    #status-container {
        height: 1;
        background: $accent;
        dock: top;
    }
    #status-container.ready {
        background: green;
    }
    #status-container.processing {
        background: orange;
    }
    ChatMessage, ToolCallMessage, ReasoningMessage {
        height: auto;
        width: 85%;
        margin: 0 0 1 0;
        overflow-x: hidden;
    }
    ReasoningMessage {
        /* Removed transition due to Scalar(unit=AUTO) animation limitation */
    }
    ReasoningMessage.collapsed {
        height: 3;
    }
    .user-container {
        align-horizontal: left;
        height: auto;
    }
    .assistant-container {
        align-horizontal: right;
        height: auto;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+c", "interrupt", "Interrupt"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+l", "clear_history", "Clear History"),
        Binding("f1", "help", "Help"),
    ]

    def __init__(self, assistant: DesktopAssistant):
        super().__init__()
        self.assistant = assistant
        self.current_assistant_message = None
        self.current_tool_message = None
        self.current_reasoning_message = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            LoadingIndicator(id="loading-indicator"),
            Static("Ready", id="status-bar"),
            id="status-container"
        )
        yield ScrollableContainer(id="chat-container")
        yield CommandSuggestor(id="command-suggestor")
        yield Vertical(
            Input(placeholder="Type your message here...", id="user-input"),
            id="input-container"
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#user-input").focus()
        self.query_one("#loading-indicator").display = False
        self.query_one("#status-container").add_class("ready")
        # Load existing history

        container = self.query_one("#chat-container")
        for msg in self.assistant.history:
            if msg["role"] == "user" and msg.get("content"):
                c = Container(ChatMessage(role=msg["role"], content=msg["content"]), classes="user-container")
                container.mount(c)
            elif msg["role"] == "assistant":
                if msg.get("content"):
                    c = Container(ChatMessage(role=msg["role"], content=msg["content"]), classes="assistant-container")
                    container.mount(c)
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        c = Container(ToolCallMessage(tool_name=tc["function"]["name"], tool_args=tc["function"]["arguments"], tool_result="Completed"), classes="assistant-container")
                        container.mount(c)
        container.scroll_end(animate=False)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update command suggestions as user types."""
        suggestor = self.query_one("#command-suggestor")
        suggestor.update_suggestions(event.value)

    async def on_command_suggestion_selected(self, message: CommandSuggestion.Selected) -> None:
        """Handle when a command is selected from the suggestor."""
        input_widget = self.query_one("#user-input")
        input_widget.value = message.command
        # Hide suggestor immediately
        self.query_one("#command-suggestor").display = False
        # Submit the input
        self.action_submit_input(message.command)

    def action_submit_input(self, value: str) -> None:
        """Process the submitted input."""
        prompt = value.strip()
        if not prompt:
            return

        if prompt.startswith("/"):
            if prompt == "/exit":
                self.exit()
            elif prompt == "/clear":
                self.action_clear_history()
            elif prompt == "/help":
                self.action_help()
            else:
                self.notify("Invalid command", severity="error")
            self.query_one("#user-input").value = ""
            return

        # Add user message to UI
        container = self.query_one("#chat-container")
        c = Container(ChatMessage(role="user", content=prompt), classes="user-container")
        container.mount(c)
        self.query_one("#user-input").value = ""
        container.scroll_end()

        # Start processing
        self.current_assistant_message = None
        self.current_reasoning_message = None
        self.run_assistant(prompt)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        self.action_submit_input(event.value)

    @work(exclusive=True)
    async def run_assistant(self, prompt: str) -> None:
        container = self.query_one("#chat-container")
        status_bar = self.query_one("#status-bar")
        status_container = self.query_one("#status-container")
        loading = self.query_one("#loading-indicator")
        
        async def callback(update: Dict[str, Any]):
            status = update.get("status")
            if status == "processing":
                status_container.remove_class("ready")
                status_container.add_class("processing")
                status_bar.update(update.get("message", "Processing..."))
                loading.display = True
            elif status == "reasoning":
                loading.display = False
                if not self.current_reasoning_message:
                    self.current_reasoning_message = ReasoningMessage()
                    c = Container(self.current_reasoning_message, classes="assistant-container")
                    container.mount(c)
                self.current_reasoning_message.content += update["content"]
                self.current_reasoning_message.refresh()
                container.scroll_end()
            elif status == "start_assistant":
                # Finalize reasoning if it exists
                if self.current_reasoning_message:
                    self.current_reasoning_message.stop_timer()
            elif status == "content":
                loading.display = False
                # Ensure reasoning timer is stopped
                if self.current_reasoning_message:
                    self.current_reasoning_message.stop_timer()
                
                if not self.current_assistant_message:
                    self.current_assistant_message = ChatMessage(role="assistant", content="")
                    c = Container(self.current_assistant_message, classes="assistant-container")
                    container.mount(c)
                self.current_assistant_message.content += update["content"]
                self.current_assistant_message.refresh()
                container.scroll_end()
            elif status == "tool_call":
                loading.display = True
                status_bar.update(f"Calling tool: {update['name']}...")
                if self.current_reasoning_message:
                    self.current_reasoning_message.stop_timer()
                self.current_tool_message = ToolCallMessage(tool_name=update['name'], tool_args=update['args'])
                c = Container(self.current_tool_message, classes="assistant-container")
                container.mount(c)
                container.scroll_end()
                # Also reset current assistant and reasoning messages so next content starts fresh
                self.current_assistant_message = None 
                self.current_reasoning_message = None
            elif status == "tool_result":
                loading.display = False
                status_bar.update(f"Tool {update['name']} finished.")
                if self.current_tool_message:
                    self.current_tool_message.tool_result = "Success"
                    self.current_tool_message.refresh()
                # Reset current messages so that the next thinking/response cycle starts fresh
                self.current_assistant_message = None 
                self.current_reasoning_message = None
            elif status == "error":
                loading.display = False
                self.notify(update["message"], severity="error", title="Error")
                status_bar.update("Error occurred")
            elif status == "interrupted":
                status_container.remove_class("processing")
                status_container.add_class("ready")
                loading.display = False
                status_bar.update("Interrupted")
                if self.current_reasoning_message:
                    self.current_reasoning_message.stop_timer()
                self.notify(update["message"], severity="warning")
            elif status == "done":
                status_container.remove_class("processing")
                status_container.add_class("ready")
                loading.display = False
                status_bar.update("Ready")
                container.scroll_end()

        await self.assistant.process_prompt(prompt, callback)



    def action_interrupt(self) -> None:
        """Interrupts the current generation worker."""
        # Find the active worker and cancel it
        for worker in self.workers:
            if worker.name == "run_assistant":
                worker.cancel()
                # Notification is handled by the callback when the task is cancelled
                return
        
        # If no worker is running, we can treat Ctrl+C as a hint to quit or just do nothing
        self.notify("No active generation to interrupt")

    def action_clear_history(self) -> None:
        self.assistant.clear_history()
        container = self.query_one("#chat-container")
        container.query(Container).remove()
        self.notify("History cleared")

    def action_help(self) -> None:
        self.notify("Ctrl+C: Interrupt | Ctrl+Q: Quit | Ctrl+L: Clear History | F1: Help", title="Help")

async def run_cli_mode(assistant: DesktopAssistant, prompt: str):
    """Runs the assistant in a simple CLI mode for a single prompt."""
    console.print(Panel(f"User: {prompt}", title="CLI Mode", border_style="green"))
    
    full_content = ""
    
    async def callback(update: Dict[str, Any]):
        nonlocal full_content
        status = update.get("status")
        if status == "processing":
            console.print(f"[yellow]{update['message']}[/yellow]")
        elif status == "reasoning":
            console.print(f"[dim cyan]{update['content']}[/dim cyan]", end="", flush=True)
        elif status == "content":
            print(update["content"], end="", flush=True)
            full_content += update["content"]
        elif status == "tool_call":
            print() # New line
            console.print(f"[grey][Tool Call:] {update['name']}({update['args']})[/grey]")
        elif status == "tool_result":
            console.print(f"[grey][Result:] {update['result']}[/grey]")
        elif status == "error":
            console.print(f"[red]Error: {update['message']}[/red]")
        elif status == "done":
            print() # New line
            console.print("[green]Finished.[/green]")

    await assistant.process_prompt(prompt, callback)

def main():
    parser = argparse.ArgumentParser(description="Desktop Assistant with Textual TUI")
    parser.add_argument("-p", "--prompt", type=str, help="Run a single prompt and exit")
    parser.add_argument("-c", "--clear", action="store_true", help="Clear chat history and exit")
    parser.add_argument("-i", "--interactive", action="store_true", default=True, help="Start interactive TUI mode (default)")
    
    args = parser.parse_args()
    
    assistant = DesktopAssistant()
    
    if args.clear:
        assistant.clear_history()
        print("History cleared.")
        if not args.prompt and not args.interactive:
            return

    if args.prompt:
        asyncio.run(run_cli_mode(assistant, args.prompt))
    else:
        app = DesktopAssistantApp(assistant)
        app.run()

if __name__ == "__main__":
    main()
