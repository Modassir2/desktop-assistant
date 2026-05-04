import json
import tiktoken

def load_config(name:str='config.json'):
    if name[-5::]!='.json':
        name+='.json'
    with open(name,'r') as file:
        config=json.load(file)
    return config

config=load_config()
MAX_TOKENS = (config.get("max_tokens") - 2500) if config.get("max_tokens") else 6000
IMAGE_TOKENS = config.get("image_tokens") if config.get("image_tokens") else 1032
n = config.get("last_n_images") if config.get("last_n_images") else 1
TOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")

def load_system_prompt(name:str='system_prompt'):
    if name[-4::]!='.txt':
        name+='.txt'
    try:
        with open(name,'r') as file:
            system_prompt=file.read()
        if not system_prompt:
            print("Warning System_prompt is empty!")
        return system_prompt    
    except FileNotFoundError:
        print("System_prompt file not found!")
        exit()

system_prompt=load_system_prompt()    

def save_history(history,name:str='history'):
    if name[-5::]!='.json':
        name+='.json'
    with open(name,'w') as file:
        json.dump(history,file,indent=4)

def load_history(name:str='history'):
    if name[-5::]!='.json':
        name+='.json'
    try:
        with open(name,'r') as file:
            history=json.load(file)
    except FileNotFoundError:
        print(f"File not found: {name}; defaulting to new history.")
        return new_history()
    return history

def load_tools(name:str='tools'):
    if name[-5::]!='.json':
        name+='.json'
    with open(name,'r') as file:
        tools=json.load(file)
    return tools

def load_memory(name:str='memory'):
    if name[-4::]!='.txt':
        name+='.txt'
    try:
        with open(name,'r') as file:
            memory=file.read()
        if not memory:
            memory=None
    except BaseException as e:
        print(f"An error occured while loading memory: {e}\nDefaulting to no memory")
        memory=None
    return memory

def append_memory(content:str,name:str="memory"):
    if name[-4::]!='.txt':
        name+='.txt'
    try:
        with open(name,'a') as file:
            file.write(content)
    except BaseException as e:
        print(f"An error occured: {e}\nMemory not added")

def rem_mem(content:str,count:int=-1,name:str='memory'):
    if name[-4::]!='.txt':
        name+='.txt'
    with open(name,'r') as file:
        mem=file.read()
    new_mem=mem.replace(content,"",count)
    with open(name,'w') as file:
        file.write(new_mem)

def update_sys_mem(history):
    global system_prompt
    memory=load_memory()
    new=system_prompt+f"Your Memory:\n{memory if memory else None}"
    history[0]['content']=new
    return history

def new_history():
    global system_prompt
    history=[{"role":"system","content":system_prompt}]
    history=update_sys_mem(history)
    return history

def count_tokens(text):
    return len(TOKEN_ENCODER.encode(str(text)))

def count_message_tokens(msg):
    tokens = 0
    
    content = msg.get('content', '')
    
    if isinstance(content, str):
        tokens += count_tokens(content)
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    tokens += count_tokens(item.get('text', ''))
                elif item.get('type') == 'image_url':
                    tokens += IMAGE_TOKENS
    
    return tokens

def truncate_history(history, max_tokens=MAX_TOKENS):
    if len(history) == 0:
        return history
    
    first_msg = history[0]
    remaining_msgs = history[1:]
    
    first_msg_tokens = count_message_tokens(first_msg)
    available = max_tokens - first_msg_tokens
    
    truncated = [first_msg]
    current_tokens = first_msg_tokens
    
    for msg in reversed(remaining_msgs):
        msg_tokens = count_message_tokens(msg)
        if current_tokens + msg_tokens <= max_tokens:
            truncated.insert(1, msg)
            current_tokens += msg_tokens
        else:
            break
    
    return truncated

def optimize_history(history):
    global n
    imgs=0;img_index_list=[];x=0
    for i in history:
        msg=i['content']
        if type(msg)==list:
            for j in msg:
                if j.get('image_url'):
                    imgs+=1
                    img_index_list.append(x)
        x+=1
    if imgs>n:
        y=len(img_index_list)-n
        for i in range(y):
            x=history[img_index_list[i]]['content']
            for j in range(len(x)):
                if x[j].get('image_url'):
                    x[j]={"type":"text","text":"Attached Image/Screenshot has been removed to save token space and processing time."}
            #history.pop(img_index_list[i])
        return history
    else:
        return history