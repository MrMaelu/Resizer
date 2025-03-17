import pygetwindow as gw
import win32gui
import win32con
import configparser
import os
import re
import toga
from toga.style.pack import COLUMN, Pack
import asyncio

"""
Window Positioner - A tool to manage window layouts and settings

This script provides a GUI to manage and apply window configurations for multiple applications.
It allows you to reposition, resize, remove title bars, and set windows as "Always on Top".

Features:
- Load and apply window configurations from .ini files
- Visual preview of window layouts
- Toggle Always-on-Top state for configured windows
- Support for multiple configuration files

Usage:
1. Place configuration files named 'config_<name>.ini' in the program directory
2. Select a configuration from the dropdown menu to preview
3. Click 'Apply' to activate the window layout
4. Use 'Toggle Always-on-Top' to change window states
5. 'Cancel' will exit and restore normal window states

Configuration Format:
[Window Title]
position = x,y         # Window position (optional)
size = width,height    # Window size (optional)
always_on_top = true/false
titlebar = true/false

Example:
[Microsoft Edge]
position = 0,0
size = 1760,1400
always_on_top = true
titlebar = false

Notes:
- Windows without position will be auto-arranged
- Window titles are matched partially and case-insensitive
"""

config = None  # Global variable to store the current configuration

def list_config_files():
    config_files = [f for f in os.listdir() if f.startswith("config_") and f.endswith(".ini")]
    config_files.sort()
    config_names = [f[7:-4] for f in config_files]  # Extract the name between 'config_' and '.ini'
    return config_files, config_names

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

                return pos, size, always_on_top, titlebar

    return None, None, None, None

topmost_windows = []
managed_windows = []  # New list to keep track of all managed windows

def apply_configured_windows(config):
    if not config or len(config.sections()) == 0:
        return False

    # Calculate auto-layout parameters
    screen_width = app.screens[0].size[0]
    screen_height = app.screens[0].size[1]
    padding = 10
    grid_size = 2

    # Collect windows by type
    positioned_windows = []
    auto_windows = []
    for section in config.sections():
        pos = config[section].get("position")
        size = config[section].get("size")
        if pos:
            positioned_windows.append(section)
        else:
            auto_windows.append(section)

    # Calculate auto-layout grid
    if auto_windows:
        windows_per_row = min(grid_size, len(auto_windows))
        window_width = (screen_width - (padding * (windows_per_row + 1))) / windows_per_row
        window_height = (screen_height - padding * 2) / ((len(auto_windows) + windows_per_row - 1) // windows_per_row)
        
        # Track auto-layout position
        current_x = padding
        current_y = padding
        col_count = 0

    global topmost_windows, managed_windows
    # Remove always-on-top status for any current config
    for hwnd in topmost_windows:
        try:
            always_on_top = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST
            if always_on_top:
                set_always_on_top(hwnd, False)
        except Exception as e:
            print("Failed to toggle always-on-top. Window might be closed.")

    # Clear the topmost_windows and managed_windows lists before applying settings
    topmost_windows = []
    managed_windows = []

    # Apply window settings
    all_titles = gw.getAllTitles()
    for section in config.sections():
        cleaned_section = clean_title(section)

        for title in all_titles:
            cleaned_title = clean_title(title)
            
            if cleaned_section in cleaned_title:
                window = gw.getWindowsWithTitle(title)[0]
                hwnd = window._hWnd
                position, size, always_on_top, titlebar = get_window_settings(section, config)

                # Restore minimized window
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

                # Apply window settings
                if always_on_top:
                    set_always_on_top(hwnd, always_on_top)
                managed_windows.append(hwnd)  # Add to managed_windows

                if not titlebar:
                    remove_titlebar(hwnd)

                # Apply size if specified
                if size:
                    window.resizeTo(size[0], size[1])

                # Apply position - either configured or auto-layout
                if position:
                    window.moveTo(position[0], position[1])
                elif section in auto_windows:
                    # Use auto-layout position
                    window.moveTo(current_x, current_y)
                    
                    # Move to next position
                    col_count += 1
                    if col_count >= windows_per_row:
                        col_count = 0
                        current_x = padding
                        current_y += window_height + padding
                    else:
                        current_x += window_width + padding

                break
    
    # Update topmost_windows list
    topmost_windows[:] = [
        hwnd for hwnd in managed_windows
        if any(
            clean_title(section) in clean_title(gw.getWindowsWithTitle(win32gui.GetWindowText(hwnd))[0].title)
            and config.has_section(section)
            and config.getboolean(section, "always_on_top", fallback=False)
            for section in config.sections()
        )
    ]
    update_always_on_top_status()
    return True

def set_always_on_top(hwnd, enable):
    try:
        flag = win32con.HWND_TOPMOST if enable else win32con.HWND_NOTOPMOST
        win32gui.SetWindowPos(hwnd, flag, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOOWNERZORDER)
        if enable and hwnd not in topmost_windows:
            topmost_windows.append(hwnd)
        elif not enable and hwnd in topmost_windows:
            topmost_windows.remove(hwnd)
        update_always_on_top_status()
    except Exception as e:
        print(f"Error setting always on top for hwnd: {hwnd}, enable: {enable}, error: {e}")

def remove_titlebar(hwnd):
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    style &= ~win32con.WS_CAPTION
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
    win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_FRAMECHANGED)

def toggle_always_on_top():
    global config  # Use the global config variable
    for hwnd in managed_windows:
        try:
            # Check if the window is configured to be always-on-top
            window_title = win32gui.GetWindowText(hwnd)
            for section in config.sections():
                if clean_title(section) in clean_title(window_title) and config.getboolean(section, "always_on_top", fallback=False):
                    always_on_top = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST
                    set_always_on_top(hwnd, not always_on_top)
                    break
        except Exception as e:
            print("Failed to toggle always-on-top. Window might be closed.")
    update_always_on_top_status()

def exit_script():
    global config  # Use the global config variable
    for hwnd in topmost_windows:
        try:
            always_on_top = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST
            if always_on_top:
                set_always_on_top(hwnd, False)
        except Exception as e:
            print("Failed to toggle always-on-top. Window might be closed.")
    
    # Stop the periodic check timer if it is running
    if hasattr(app, 'periodic_check_task') and app.periodic_check_task:
        app.periodic_check_task.cancel()
    
    os._exit(0)

# Function to check if windows exist
def check_windows_exist(config):
    all_titles = gw.getAllTitles()
    existing_windows = []
    missing_windows = []

    for section in config.sections():
        cleaned_section = clean_title(section)
        window_exists = any(cleaned_section in clean_title(title) for title in all_titles)
        if window_exists:
            existing_windows.append(section)
        else:
            missing_windows.append(section)

    return existing_windows, missing_windows

# Function to update window status on the drawing
def update_window_status(config, existing_windows, missing_windows):
    def config_draw(context, w, h):
        draw_screen_layout(screen_canvas, context, w, h, config, existing_windows, missing_windows)
    
    # Check if the current draw function is different from the new one
    if screen_canvas.draw != config_draw:
        screen_canvas.draw = config_draw
        config_draw(screen_canvas.context, screen_canvas.style.width, screen_canvas.style.height)
        screen_canvas.refresh()

# GUI setup

def on_config_select(widget):
    global config  # Use the global config variable
    try:
        selected_config = config_files[config_names.index(widget.value)]
        config = load_config(selected_config)
        if not config:
            print("Error: Could not load configuration.")
            return
        
        existing_windows, missing_windows = check_windows_exist(config)
        
        # Update canvas with window layout
        def config_draw(context, w, h):
            draw_screen_layout(screen_canvas, context, w, h, config, existing_windows, missing_windows)
            
        screen_canvas.draw = config_draw
        config_draw(screen_canvas.context, screen_canvas.style.width, screen_canvas.style.height)
        screen_canvas.refresh()
        
    except Exception as e:
        print(f"Config selection error: {e}")
        import traceback
        traceback.print_exc()

async def periodic_check_windows_exist():
    while True:
        await asyncio.sleep(5)
        try:
            existing_windows, missing_windows = check_windows_exist(config)
            update_window_status(config, existing_windows, missing_windows)
        except Exception as e:
            print(f"Periodic check error: {e}")

def apply_settings(widget):
    global config  # Use the global config variable
    selected_config = config_files[config_names.index(config_dropdown.value)]
    config = load_config(selected_config)
    if config:
        apply_configured_windows(config)
        if topmost_windows:
            box.add(toggle_button)
        
        # Stop the existing periodic check timer if it is running
        if hasattr(app, 'periodic_check_task') and app.periodic_check_task:
            app.periodic_check_task.cancel()
        
        # Start a new periodic check timer with the new configuration
        app.periodic_check_task = asyncio.create_task(periodic_check_windows_exist())

        update_always_on_top_status()  # Update the always-on-top status

def cancel_settings(widget):
    exit_script()

def toggle_always_on_top_button(widget):
    toggle_always_on_top()
    update_always_on_top_status()

def update_always_on_top_status():
    status = "Always-on-Top: "
    if not topmost_windows:
        status += "Disabled"
    else:
        is_enabled = False
        for hwnd in topmost_windows:
            if win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST:
                is_enabled = True
                break
        status += "Enabled" if is_enabled else "Disabled"
        
    setattr(always_on_top_status, 'text', status)

def draw_screen_layout(canvas, context, w, h, config, existing_windows, missing_windows):
    try:
        # Setup background and border
        with context.Fill(color='white') as fill:
            fill.rect(0, 0, w, h)
        with context.Stroke(color='black', line_width=2) as stroke:
            stroke.rect(5, 5, w-10, h-10)
        
        if not config or not config.sections():
            return
            
        # Get screen dimensions and calculate usable area
        screen_width = app.screens[0].size[0]
        screen_height = app.screens[0].size[1]
        padding = 10
        usable_width = w - (padding * 2)
        usable_height = h - (padding * 2)
        
        # Collect windows by type
        positioned_windows = []
        auto_windows = []
        
        for section in config.sections():
            pos = config[section].get("position")
            size = config[section].get("size")
            if pos and size:
                positioned_windows.append((section, pos, size))
            else:
                auto_windows.append(section)
        
        # Draw positioned windows
        for section, pos, size in positioned_windows:
            try:
                pos_x, pos_y = map(int, pos.split(','))
                size_w, size_h = map(int, size.split(','))
                always_on_top = config[section].get("always_on_top", "false").lower() == "true"
                window_exists = section in existing_windows
                
                # Scale to canvas
                scaled_x = (pos_x / screen_width) * usable_width + padding
                scaled_y = (pos_y / screen_height) * usable_height + padding
                scaled_w = (size_w / screen_width) * usable_width
                scaled_h = (size_h / screen_height) * usable_height
                
                draw_window_box(context, section, scaled_x, scaled_y, scaled_w, scaled_h,
                              pos_x, pos_y, size_w, size_h, always_on_top, window_exists)
            except Exception as e:
                print(f"Error drawing positioned window {section}: {e}")
        
        # Handle auto-positioned windows
        if auto_windows:
            grid_size = 2
            windows_per_row = min(grid_size, len(auto_windows))
            window_width = (usable_width - (padding * (windows_per_row - 1))) / windows_per_row
            window_height = (usable_height - padding) / ((len(auto_windows) + windows_per_row - 1) // windows_per_row)
            
            current_x = padding
            current_y = padding
            col_count = 0
            
            for section in auto_windows:
                try:
                    always_on_top = config[section].get("always_on_top", "false").lower() == "true"
                    window_exists = section in existing_windows
                    real_x = int(current_x * screen_width / usable_width)
                    real_y = int(current_y * screen_height / usable_height)
                    real_w = int(window_width * screen_width / usable_width)
                    real_h = int(window_height * screen_height / usable_height)
                    
                    draw_window_box(context, section, current_x, current_y, window_width, window_height,
                                  real_x, real_y, real_w, real_h, always_on_top, window_exists)
                    
                    # Move to next position
                    col_count += 1
                    if col_count >= windows_per_row:
                        col_count = 0
                        current_x = padding
                        current_y += window_height + padding
                    else:
                        current_x += window_width + padding
                        
                except Exception as e:
                    print(f"Error drawing auto-positioned window {section}: {e}")
                    
    except Exception as e:
        print(f"Draw error: {e}")
        import traceback
        traceback.print_exc()

def draw_window_box(context, title, x, y, w, h, real_x, real_y, real_w, real_h, always_on_top, window_exists):
    try:
        # Draw box
        with context.Fill(color='lightblue' if not always_on_top else 'lightgreen') as fill:
            fill.rect(x, y, w, h)
        with context.Stroke(color='blue' if not always_on_top else 'green') as stroke:
            stroke.rect(x, y, w, h)
        
        # Text layout parameters
        text_x = int(x + 5)
        text_y = int(y + 15)  # Start text 15px from top
        line_height = 20  # Space between lines
        
        # Format text same as previous settings display
        pos_text = f"X {real_x}, Y {real_y}"
        size_text = f"{real_w} x {real_h}"
        
        # Draw text lines
        text_lines = [
            title,
            f"Position: {pos_text}",
            f"Size: {size_text}",
            f"Always-on-top: {'Yes' if always_on_top else 'No'}"
        ]
        
        # Draw each line using Fill context
        for i, line in enumerate(text_lines):
            y_pos = text_y + (i * line_height)
            with context.Fill(color='rgba(0, 0, 0, 1)') as fill:
                fill.write_text(line, text_x, y_pos)
        
        # Draw "missing" in red if the window does not exist
        if not window_exists:
            with context.Fill(color='red') as fill:
                fill.write_text("\nMissing", text_x, text_y + (len(text_lines) * line_height))
        
    except Exception as e:
        print(f"Error drawing window box: {str(e)}")
        import traceback
        traceback.print_exc()

def create_gui(app):
    global box, config_dropdown, toggle_button, always_on_top_status, config_files, config_names, screen_canvas

    try:
        # Define main container
        box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # Get screen dimensions for scaling
        screen_width = app.screens[0].size[0]
        screen_height = app.screens[0].size[1]

        # Create header section
        header_box = toga.Box(style=Pack(direction=COLUMN, padding=5))
        
        # Define dropdown
        config_files, config_names = list_config_files()
        if not config_files:
            raise ValueError("No configuration files found")
            
        config_dropdown = toga.Selection(
            items=config_names, 
            on_change=lambda widget: on_config_select(widget),
            style=Pack(flex=1, padding=(0,0,5,0))
        )
        header_box.add(config_dropdown)
        
        screen_info = f"Screen: {screen_width} x {screen_height}"
        screen_dimensions_label = toga.Label(
            screen_info,
            style=Pack(padding=(0,0,5,0))
        )
        header_box.add(screen_dimensions_label)

        # Define canvas with fixed aspect ratio
        canvas_height = 200
        canvas_width = int(canvas_height * (screen_width/screen_height))
        screen_canvas = toga.Canvas(
            style=Pack(
                padding=5,
                height=canvas_height,
                width=canvas_width,
                flex=1,
                background_color='#cccccc'
            )
        )
        
        # Set initial draw state
        def initial_canvas_state(context, w, h):
            with context.Fill(color='white') as fill:
                fill.rect(0, 0, w, h)
            with context.Stroke(color='black', line_width=2) as stroke:
                stroke.rect(5, 5, w-10, h-10)
            context.write_text("Select a configuration", w/2 - 60, h/2)
            
        screen_canvas.draw = initial_canvas_state
        initial_canvas_state(screen_canvas.context, canvas_width, canvas_height)
        screen_canvas.refresh()

        # Create button container
        button_box = toga.Box(style=Pack(direction='row', padding=5))

        # Define status label
        always_on_top_status = toga.Label(
            "Always-on-Top: Disabled",
            style=Pack(padding=5)
        )

        # Define buttons
        apply_button = toga.Button('Apply', on_press=apply_settings, style=Pack(padding=2, flex=1))
        cancel_button = toga.Button('Cancel', on_press=cancel_settings, style=Pack(padding=2, flex=1))
        toggle_button = toga.Button('Toggle Always-on-Top', on_press=toggle_always_on_top_button, style=Pack(padding=2))
        
        button_box.add(apply_button)
        button_box.add(cancel_button)

        # Assemble the layout
        box.add(header_box)
        box.add(screen_canvas)
        box.add(button_box)
        box.add(always_on_top_status)

        # Configure window
        app.main_window.content = box
        app.main_window.size = (700, 400)
        app.main_window.position = (
            (screen_width // 2) - (app.main_window.size[0] // 2),
            (screen_height // 2) - (app.main_window.size[1] // 2)
        )

        # Set initial value and trigger selection
        config_dropdown.value = config_names[0]
        on_config_select(config_dropdown)
        
        update_always_on_top_status() # Initialize the label
        return box

    except Exception as e:
        print(f"Error creating GUI: {e}")
        import traceback
        traceback.print_exc()
        return None

def show_menu():
    global app
    app = toga.App('Window Positioner', 'Window Positioner', startup=create_gui)
    return app

# End of GUI setup

def main():
    # First check for config_ files
    config_files, _ = list_config_files()
    
    if not config_files:
        # Look for legacy config.ini
        if os.path.exists('config.ini'):
            print("Found legacy config.ini, applying settings...")
            config = load_config('config.ini')
            if config and apply_configured_windows(config):
                print("Settings applied successfully")
                return
            else:
                print("Failed to apply settings from config.ini")
    
    # If no valid config found or config_ files exist, show GUI
    show_menu().main_loop()

if __name__ == "__main__":
    main()
