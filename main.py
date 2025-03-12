import pygetwindow as gw
import win32gui
import win32con
import keyboard
import time
from pynput.mouse import Listener
import configparser
import os
import re
import ctypes, sys

"""
This script allows users to reposition, resize, remove the title bar, and set windows as "Always on Top".

Usage:
1. If a valid config.ini exists with at least one application defined, the script will apply those settings automatically.
2. If no valid configuration is found, the user will be prompted to click on a window, which will be set to the default values.
3. Use 'Ctrl + Alt + T' to toggle Always on Top for any window that was initially set as Always on Top.
4. If no window is set as Always on Top in the config, the script will exit.

Configuration:
- Create a 'config.ini' file in the same directory.
- Example format:

[Microsoft Edge]
position = 0,0
size = 1760,1400
always_on_top = true
titlebar = false

[Discord]
position = 4320,0
size = 800,1400
always_on_top = false
titlebar = true

"""
# Click-to-select defaults
default_position = (1760, 0)
default_size = (2560, 1440)
default_always_on_top = True
default_titlebar = False


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def list_config_files():
    config_files = [f for f in os.listdir() if f.startswith("config_") and f.endswith(".ini")]
    config_files.sort()
    return config_files

def select_config_file():
    config_files = list_config_files()
    if not config_files:
        print("No config files found. Using default config.ini.")
        return "config.ini"
    
    print("Select a config file:")
    for i, file in enumerate(config_files):
        config = configparser.ConfigParser()
        config.read(file)
        apps = ", ".join(config.sections())
        print(f"{i + 1}. {file[7:-4]} (Applications: {apps})")
    
    choice = int(input("Enter the number of the config file to use (0 for default): ")) - 1
    if 0 <= choice < len(config_files):
        return config_files[choice]
    elif choice == -1:
        print("Using default config.ini.")
        return "config.ini"
    else:
        print("Invalid choice. Using default config.ini.")
        return "config.ini"

def load_config(config_path):
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
        return config
    return None

def clean_title(title):
    # Remove non-printable characters, zero-width spaces, and normalize spacing
    title = re.sub(r'[^\x20-\x7E]', '', title)  # Remove non-printable characters
    title = re.sub(r'\s+', ' ', title)  # Normalize multiple spaces to a single space
    return title.strip().lower()  # Lowercase and trim spaces

def get_window_settings(title, config):
    global config_file
    
    if config:
        for section in config.sections():
            if clean_title(section) in clean_title(title):
                pos = config[section].get("position", fallback=None)
                size = config[section].get("size", fallback=None)
                always_on_top = config[section].get("always_on_top", "false").lower() == "true"
                titlebar = config[section].get("titlebar", "true").lower() == "true"

                if pos:
                    pos = tuple(map(int, pos.split(",")))
                if size:
                    size = tuple(map(int, size.split(",")))

                print(f"Applying settings from {config_file} for {section} -> Position: {pos}, Size: {size}, Always on Top: {always_on_top}, Titlebar: {titlebar}")
                return pos, size, always_on_top, titlebar

    return None, None, None, None

topmost_windows = []

def apply_configured_windows(config):
    if not config or len(config.sections()) == 0:
        return False
    
    all_titles = gw.getAllTitles()
    
    for section in config.sections():
        cleaned_section = clean_title(section)
        
        for title in all_titles:
            cleaned_title = clean_title(title)
            
            if cleaned_section in cleaned_title:
                window = gw.getWindowsWithTitle(title)[0]
                hwnd = window._hWnd
                position, size, always_on_top, titlebar = get_window_settings(section, config)
                set_always_on_top(hwnd, always_on_top)

                if not titlebar:
                    remove_titlebar(hwnd)

                if size:
                    window.resizeTo(size[0], size[1])

                if position:
                    window.moveTo(position[0], position[1])

                if always_on_top:
                    topmost_windows.append(hwnd)

                break
    
    return True

def set_always_on_top(hwnd, enable):
    flag = win32con.HWND_TOPMOST if enable else win32con.HWND_NOTOPMOST
    win32gui.SetWindowPos(hwnd, flag, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

def remove_titlebar(hwnd):
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    style &= ~win32con.WS_CAPTION
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
    win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_FRAMECHANGED)

def on_click(x, y, button, pressed):
    global selected_window
    if pressed:
        windows = gw.getWindowsAt(x, y)
        if windows:
            selected_window = windows[0]
            hwnd = selected_window._hWnd
            selected_window.resizeTo(default_size[0], default_size[1])
            selected_window.moveTo(default_position[0], default_position[1])
            set_always_on_top(hwnd, True)
            topmost_windows.append(hwnd)
            remove_titlebar(hwnd)
            print(f"No config found, applying default settings.")
        return False

def listen_for_hotkeys():
    if not topmost_windows:
        print("No windows were set as Always on Top. Exiting.")
        return
    
    keyboard.add_hotkey("ctrl+alt+t", toggle_always_on_top)
    keyboard.add_hotkey("ctrl+alt+q", exit_script)
    print("Press Ctrl + Alt + T to toggle Always on Top for configured windows, or Ctrl + Alt + Q to exit.")
    while True:
        time.sleep(1)

def toggle_always_on_top():
    for hwnd in topmost_windows:
        always_on_top = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST
        set_always_on_top(hwnd, not always_on_top)

def exit_script():
    print("Exiting script...")
    for hwnd in topmost_windows:
        always_on_top = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST
        if always_on_top:
            toggle_always_on_top()
    os._exit(0)

def main():
    global config_file
    config_file = select_config_file()
    config = load_config(config_file)
    if not apply_configured_windows(config):
        print("No valid config found, click on a window to apply default settings.")
        with Listener(on_click=on_click) as listener:
            listener.join()
    listen_for_hotkeys()

if __name__ == "__main__":
    if is_admin():
        main()
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
