import json
import pyautogui
import mss
import colorama
import base64
import time
from openai import OpenAI
import utils
import win32gui
import win32con
import cv2
import numpy as np

colorama.init(autoreset=True)
GREY = colorama.Fore.LIGHTBLACK_EX
CYAN = colorama.Fore.CYAN
GREEN = colorama.Fore.GREEN
LIGHTGREEEN = colorama.Fore.LIGHTGREEN_EX
RED = colorama.Fore.LIGHTRED_EX
YELLOW = colorama.Fore.YELLOW
RESET = colorama.Fore.RESET

tools = utils.load_tools()
config = utils.load_config()
dev_mode=config.get("dev_mode") if config.get("dev_mode") else False
client = OpenAI(base_url=config.get("base_url"), api_key=config.get("api_key"))
#model= "qwen/qwen3-vl-8b"
#model= "qwen3-vl-30b-a3b-instruct"
model=config.get("model")
w = config.get("width") if config.get("width") else 1920
h = config.get("height") if config.get("height") else 1080
mon=config.get("monitor") if config.get("monitor") else 1
system_prompt=utils.load_system_prompt()

#history=[{'role':'system','content':system_prompt}]
history=utils.load_history()
history=utils.optimize_history(history)
utils.save_history(history)
user_turn = True

#HELPER FUNCTIONS
def get_screenshot(mon:int=mon):
    with mss.mss() as screen:
        screen.shot(output="monitor-2.png", mon=mon)
    with open('monitor-2.png','rb') as img:
        base64img=base64.b64encode(img.read()).decode('utf-8')
    return f"data:image/jpeg;base64,{base64img}"

def annonated_cursor(image_url:str=get_screenshot(),coords:list=pyautogui.position()):
    image_b64=image_url[23::]
    x,y=coords
    #Decode base64 string to OpenCV image
    img_data = base64.b64decode(image_b64)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    #Crosshair parameters
    color = (0, 0, 255) #Moda dont forget -> BGR not RGB
    thickness = 2
    size = 12
    #Draw horizontal and vertical lines (+)
    cv2.line(img, (x - size, y), (x + size, y), color, thickness)
    cv2.line(img, (x, y - size), (x, y + size), color, thickness)
    # 4. Re-encode image back to base64
    _, buffer = cv2.imencode('.png', img)
    base64img = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{base64img}"

def _get_open_apps_raw():
    windows = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                windows.append((title, hwnd))
        return True
    win32gui.EnumWindows(callback, None)
    return windows

def focus_window(app_name):
    current_hwnd = win32gui.GetForegroundWindow() 
    windows = _get_open_apps_raw()
    name_lower = app_name.lower()
    for title, hwnd in windows:
        if name_lower in title.lower():
            if hwnd == current_hwnd:
                return True
            win32gui.SetForegroundWindow(hwnd)
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            return True
    return False

#DEBUGGING FUNCTIONS
def display_img(base64_image: str):
    img_data = base64.b64decode(base64_image)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    cv2.imshow("Test Crosshair Placement", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

#FUNCTIONS FOR MODEL
def check_coordinates(coordinates:list,place:str):
    try:
        x,y=coordinates
    except ValueError as e:
        return [{'role':"tool","name":"left_click","content":f"Invalid argument passed: {e}"}]
    x_pixel=int((x/1000)*w)
    y_pixel=int((y/1000)*h)
    image_url=annonated_cursor(coords=[x_pixel,y_pixel])
    return [{
        "role":"tool",
        "name":"check_coordinates",
        "content":[
            {"type":"text","text":f"The given coordinates corresponds to the RED + marker on the image."},
            {"type":"image_url","image_url":{"url":image_url}}
        ]
    }]

def l_click(coordinates:list,reason:str="Not Specified",wait:int=3):
    try:
        x,y=coordinates
    except ValueError as e:
        return [{'role':"tool","name":"left_click","content":f"Invalid argument passed: {e}"}]
    x_pixel=int((x/1000)*w)
    y_pixel=int((y/1000)*h)
    pyautogui.click(x_pixel, y_pixel)
    time.sleep(wait)
    image_url=get_screenshot()
    return [{
        "role":"tool",
        "name":"l_click",
        "content":[
            {"type":"text","text":f"Clicked at {x},{y}. Updated screen after clicking on screen"},
            {"type":"image_url","image_url":{"url":image_url}}
        ]
    }]

def r_click(coordinates:list,reason:str="Not Specified",wait:int=3):
    try:
        x,y=coordinates
    except ValueError as e:
        return [{'role':"tool",
                 "name":"right_click",
                 "content":[{"type":"text","text":f"Invalid argument passed: {e}"}]
            }]
    x_pixel=int((x/1000)*w)
    y_pixel=int((y/1000)*h)
    pyautogui.rightClick(x_pixel, y_pixel)
    if wait:
        time.sleep(wait)
    image_url=get_screenshot()
    return [{
        "role":"tool",
        "name":"r_click",
        "content":[
            {"type":"text","text":f"Right Clicked at {x},{y}. Updated screen after right clicking on screen"},
            {"type":"image_url","image_url":{"url":image_url}}
        ]
    }]

def view_screen():
    image_url=get_screenshot()
    return [{
        "role":"tool",
        "name":"view_screen",
        "content":[
            {"type":"image_url","image_url":{"url":image_url}}
        ]
    }]

def type_text(text:str,press_enter:bool=False,wait:int=2,reason:str="Not Specified"):
    pyautogui.write(text)
    time.sleep(1)
    if press_enter:
        pyautogui.hotkey(['enter'])
    time.sleep(wait)
    image_url=get_screenshot()
    return [{
        "role":"tool",
        "name":"type_text",
        "content":[
            {"type":"text","text":f"Typed: {text if len(text)<=1001 else text[:1000:]+'...'}. Updated screen after typing text"},
            {"type":"image_url","image_url":{"url":image_url}}
        ]
    }]

def press_keyboard_buttons(shortcut:list,app_name:str,reason:str="Not Specified",wait:int=0):
    if app_name.lower()=='none':
        app_name=None
    if app_name:
        status=focus_window(app_name)
        if status==False:
            return [{'role':'tool','name':'press_keyboard_buttons',"content":[{"type":"text","text":f"App not found: {app_name}.List of Open Apps:\n{_get_open_apps_raw()}"}]}]
    key_str=" + ".join(shortcut)
    try:
        pyautogui.hotkey(shortcut)
        if wait:
            time.sleep(wait)
        image_url=get_screenshot()
        return [{
            "role":"tool",
            "name":"press_keyboard_buttons",
            "content":[
                {"type":"text","text":f"Successfully executed: {key_str.strip()}. Updated screen after pressing keyboard keys"},
                {"type":"image_url","image_url":{"url":image_url}}
            ]
        }]
    except ValueError as e:
        return [{'role':'tool','name':'press_keyboard_buttons','content':[{"type":"text","text":f"Invalid shortcut: {key_str}; {e}"}]}]
    except pyautogui.FailSafeException as e:
        return [{'role':'tool','name':'press_keyboard_buttons','content':[{"type":"text","text":f"Fail Safe Exception: {e}"}]}]
    
'''
def get_permission(question:str):
    global user_permission
    print(f"{YELLOW}[QUESTION]\n{question}{RESET}")
    l=input(f"{RED}Answer: {RESET}").split()
    if '/allow' in l or 'yes' in l or 'yup' in l or 'yep' in l or 'sure' in l:
        answer=" ".join(l)
        user_permission=True
        return [{'role':'tool','name':'question_user','content':[{"type":"text","text":f"User allowed Permission: {answer}"}]}]
    else:
        answer=" ".join(l)
        return [{'role':'tool','name':'question_user','content':[{"type":"text","text":f"User denied Permission: {answer}"}]}]
'''
    
def scroll(coordinates:list,reason:str=None,amount:int=6,direction_down:bool=True,wait:int=2):
    x,y=coordinates
    pixel_x=int((x/1000)*w)
    pixel_y=int((y/1000)*h)
    amount*=50
    pyautogui.moveTo(pixel_x,pixel_y)
    if direction_down:
        pyautogui.scroll(-amount)
    else:
        pyautogui.scroll(amount)
    time.sleep(wait)
    image_url=annonated_cursor()
    return [
        {
            "role":"tool",
            "name":"scroll",
            "content":[
                {"type":"text","text":f"Successfully scrolled {amount} units {'down' if direction_down else 'up'} at ({x},{y}). Updated screen after scrolling"},
                {"type":"image_url","image_url":{"url":image_url}}
            ]
        }
    ]

def add_memory(content:str):
    content='\n'+content
    utils.append_memory(content)
    return [
        {
            "role":"tool",
            "name":"add_memory",
            "content":[
                {"type":"text","text":f"Successfully added to memory"}
            ]
        }
    ]

def remove_memory(content:str,count:int=-1):
    utils.rem_mem(content,count)
    return [
        {
            "role":"tool",
            "name":"remove_memory",
            "content":[
                {"type":"text","text":f"Successfully removed from memory"}
            ]
        }
    ]

def wait(interval:int,reason:str=None):
    time.sleep(interval)
    image_url=get_screenshot()
    return [
        {
            "role":"tool",
            "name":"wait",
            "content":[
                {"type":"text","text":f"Wait period of {interval}s is finished. Updated screen after waiting"},
                {"type":"image_url","image_url":{"url":image_url}}
            ]
        }
    ]

tool_map = {
    "view_screen": view_screen,
    "type_text": type_text,
    "press_keyboard_buttons":press_keyboard_buttons,
    "check_coordinates":check_coordinates,
    "left_click":l_click,
    "right_click":r_click,
    "scroll":scroll,
    "add_memory":add_memory,
    "remove_memory":remove_memory,
    "wait":wait
}

if __name__=="__main__":
    time.sleep(3)
    display_img(base64_image=annonated_cursor())
    exit()