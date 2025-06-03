import pygetwindow as gw
import win32api
import win32gui
import win32con
import configparser
import os
import sys
import re
import toga
from toga.style.pack import COLUMN, Pack, BOLD, SERIF, SANS_SERIF, ROW
import asyncio
from asyncio import Lock
import time
import threading

def restart_as_admin(widget):
    if sys.platform == "win32":
        import ctypes
        params = " ".join([f'"{arg}"' for arg in sys.argv])
        # ShellExecuteW returns >32 if successful
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
        if rc > 32:
            os._exit(0)

is_dragging = False

# globals
config = None
screen_width = 0
screen_height = 0
selected_window_button = None
status_label = None
waiting_for_window_selection = False
selected_window_hwnd = None

if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

config_dir = os.path.join(base_path, "configs")
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

def get_screen_resolution():
    global screen_width, screen_height
#    max_screen_height = 0
    if screen_width == 0:
        for screen in app.screens:
            screen_width += screen.size[0]
        screen_height = app.screens[0].size[1]

def list_config_files():
    config_files = [f for f in os.listdir(config_dir) if f.startswith("config_") and f.endswith(".ini")]
    config_files.sort()
    config_names = [f[7:-4] for f in config_files]
    return config_files, config_names

def load_config(config_path):
    config = configparser.ConfigParser()
    try:
        if os.path.exists(os.path.join(config_dir, config_path)):
            config.read(os.path.join(config_dir, config_path))
            return config
        return None
    except Exception as e:
        print(f"Error loading config file {config_path}: {e}")
        import traceback
        traceback.print_exc()
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
managed_windows = []

def apply_configured_windows(config):
    # Applies window configurations from the given config to the currently open windows.
    try:
        global screen_width, screen_height
        get_screen_resolution()
        
        if not config or len(config.sections()) == 0:
            return False

        # Calculate auto-layout parameters
        padding = 1
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
                        try:
                            set_always_on_top(hwnd, always_on_top)
                        except Exception as e:
                            print(f"Error setting always on top for hwnd: {hwnd}, error: {e}")
                            import traceback
                            traceback.print_exc()
                    managed_windows.append(hwnd)  # Add to managed_windows

                    if not titlebar:
                        try:
                            remove_titlebar(hwnd)
                        except Exception as e:
                            print(f"Error removing titlebar for hwnd: {hwnd}, error: {e}")
                            import traceback
                            traceback.print_exc()

                    # Apply size if specified
                    if size:
                        try:
                            window.resizeTo(size[0], size[1])
                        except Exception as e:
                            print(f"Error resizing window for hwnd: {hwnd}, error: {e}")
                            import traceback
                            traceback.print_exc()

                    # Apply position - either configured or auto-layout
                    if position:
                        try:
                            window.moveTo(position[0], position[1])
                        except Exception as e:
                            print(f"Error moving window for hwnd: {hwnd}, error: {e}")
                            import traceback
                            traceback.print_exc()
                    elif section in auto_windows:
                        # Use auto-layout position
                        try:
                            window.moveTo(int(current_x), int(current_y))
                        except Exception as e:
                            print(f"Error moving window for hwnd: {hwnd}, error: {e}")
                            import traceback
                            traceback.print_exc()
                        
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
    except Exception as e:
        print(f"Error applying configured windows: {e}")
        import traceback
        traceback.print_exc()
        return False

def set_always_on_top(hwnd, enable):
    try:
        flag = win32con.HWND_TOPMOST if enable else win32con.HWND_NOTOPMOST
        win32gui.SetWindowPos(hwnd, flag, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOOWNERZORDER)
        if enable and hwnd not in topmost_windows:
            topmost_windows.append(hwnd)
            #print(f"Added hwnd {hwnd} to topmost_windows")
        elif not enable and hwnd in topmost_windows:
            topmost_windows.remove(hwnd)
            #print(f"Removed hwnd {hwnd} from topmost_windows")
        update_always_on_top_status()
    except Exception as e:
        print(f"Error setting always on top for hwnd: {hwnd}, enable: {enable}, error: {e}")
        import traceback
        traceback.print_exc()

def remove_titlebar(hwnd):
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    try:
        style &= ~win32con.WS_CAPTION
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_FRAMECHANGED)
    except Exception as e:
        print(f"Error removing titlebar for hwnd: {hwnd}, error: {e}")
        import traceback
        traceback.print_exc()

def restore_titlebar(hwnd):
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        # Check if WS_CAPTION is already present to avoid adding it multiple times
        if not (style & win32con.WS_CAPTION):
            style |= win32con.WS_CAPTION
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            # Force redraw to show the title bar
            win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_FRAMECHANGED | win32con.SWP_SHOWWINDOW)
            #print(f"Restored titlebar for hwnd: {hwnd}")
    except Exception as e:
        print(f"Error restoring titlebar for hwnd: {hwnd}, error: {e}")
        import traceback
        traceback.print_exc()

def toggle_always_on_top():
    global config
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

def start_window_selection(widget):
    global waiting_for_window_selection, status_label, app
    global apply_button, select_window_button, toggle_button, config_dropdown

    waiting_for_window_selection = True
    status_label.text = "Click on the target window..."

    # Disable buttons while selecting
    apply_button.enabled = False
    select_window_button.enabled = False
    toggle_button.enabled = False
    config_dropdown.enabled = False

    # Reset any currently applied settings
    reset_all_managed_windows()

    # Start listening for the click in a separate thread
    # Using a thread because Toga's main loop might block win32api calls
    click_listener_thread = threading.Thread(target=listen_for_window_click, daemon=True)
    click_listener_thread.start()

def reset_all_managed_windows():
    global managed_windows, topmost_windows

    # Combine lists and remove duplicates
    all_hwnds_to_reset = list(set(managed_windows + topmost_windows))

    for hwnd in all_hwnds_to_reset:
        try:
            if not win32gui.IsWindow(hwnd):
                continue

            # Reset Always on Top
            if win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST:
                set_always_on_top(hwnd, False) # set_always_on_top handles removal from topmost_windows

            # Restore Titlebar (check if it was removed by looking for WS_CAPTION)
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if not (style & win32con.WS_CAPTION):
                 restore_titlebar(hwnd)

        except Exception as e:
            print(f"Error resetting window {hwnd}: {e}")
            # Continue with the next window

    # Clear the lists after processing
    managed_windows = []
    topmost_windows = [] # set_always_on_top should have cleared this, but clear again just in case
    update_always_on_top_status() # Update the status label

def exit_script():
    global app
    os._exit(0)

# Check if windows exist
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

# Update window status on the drawing
def update_window_status(config, existing_windows, missing_windows):
    def config_draw(context, w, h):
        draw_screen_layout(screen_canvas, context, w, h, config, existing_windows, missing_windows)
    
    # Check if the current draw function is different from the new one
    if screen_canvas.draw != config_draw:
        screen_canvas.draw = config_draw
        config_draw(screen_canvas.context, screen_canvas.style.width, screen_canvas.style.height)
        screen_canvas.refresh()

def listen_for_window_click():
    global waiting_for_window_selection, selected_window_hwnd, app

    # Get the HWND of our Toga application window to ignore clicks on it
    app_hwnd = None
    try:
        # Attempt to find the main visible Toga window by title
        toga_windows = gw.getWindowsWithTitle(app.formal_name)
        if toga_windows:
            for win in toga_windows:
                # Ensure it's a top-level, visible window
                if win32gui.IsWindowVisible(win._hWnd) and win32gui.GetParent(win._hWnd) == 0:
                    app_hwnd = win._hWnd
                    break
        if not app_hwnd:
             print("Warning: Could not reliably get Toga window handle. Self-clicks might still be registered.")

    except Exception as e:
        print(f"Error getting Toga window handle: {e}")
        app_hwnd = None # Proceed without it if error occurs

    while waiting_for_window_selection:
        # Check for left mouse button down state (VK_LBUTTON = 0x01)
        # GetAsyncKeyState returns a short integer. The high-order bit indicates if the key is down.
        if win32api.GetAsyncKeyState(0x01) & 0x8000:
            # Get cursor position and the window handle at that position
            cursor_pos = win32gui.GetCursorPos()
            hwnd_at_cursor = win32gui.WindowFromPoint(cursor_pos)

            # Check if the click is on a valid window and not our app window
            if hwnd_at_cursor and hwnd_at_cursor != app_hwnd:
                # Get the top-level parent window
                root_hwnd = win32gui.GetAncestor(hwnd_at_cursor, win32con.GA_ROOT)
                if root_hwnd and root_hwnd != app_hwnd:
                    selected_window_hwnd = root_hwnd
                    # Schedule the handler to run in the main GUI thread
                    app.loop.call_soon_threadsafe(handle_window_selection)
                    break # Exit loop once click is detected

        # Small sleep to prevent high CPU usage
        time.sleep(0.1)

def handle_window_selection():
    global waiting_for_window_selection, selected_window_hwnd, status_label, selected_window_name
    global apply_button, select_window_button, toggle_button, config_dropdown

    waiting_for_window_selection = False # Exit selection mode

    window_modified = False # Flag to track if modifications were applied

    if selected_window_hwnd and win32gui.IsWindow(selected_window_hwnd):
        try:
            selected_window_name = win32gui.GetWindowText(selected_window_hwnd)
            #print(f"Window selected: '{selected_window_name}' (HWND: {selected_window_hwnd})")

            # --- Apply modifications ---
            #print(f"Applying Always on Top to {selected_window_hwnd}")
            set_always_on_top(selected_window_hwnd, True)
            # Note: set_always_on_top adds to topmost_windows, which might be confusing
            # as this window isn't managed by a config. We might need to adjust reset logic later if needed.

            #print(f"Removing titlebar from {selected_window_hwnd}")
            remove_titlebar(selected_window_hwnd)
            # --- End modifications ---

            window_modified = True # Mark as modified

            if status_label:
                status_label.text = f"Applied to: '{selected_window_name[:30]}...'"

        except Exception as e:
            print(f"Error getting window title or applying changes: {e}")
            if status_label: status_label.text = "Error applying changes."
            # Attempt to reset if modification started but failed? Maybe not necessary here.
            selected_window_hwnd = None
            selected_window_name = None
    else:
        print("Invalid or no window selected.")
        if status_label: status_label.text = "Window selection failed or cancelled."
        selected_window_hwnd = None
        selected_window_name = None

    # Re-enable buttons and dropdown (safely)
    if apply_button: apply_button.enabled = True
    if select_window_button: select_window_button.enabled = True
    if toggle_button and config:
         toggle_button.enabled = any(config.getboolean(section, "always_on_top", fallback=False) for section in config.sections())
    elif toggle_button:
         toggle_button.enabled = False
    if config_dropdown: config_dropdown.enabled = True

    # If modifications failed, clear the status label after re-enabling buttons
    if not window_modified and status_label and status_label.text == "Error applying changes.":
         # Optionally add a small delay or just clear it
         # app.loop.call_later(2, lambda: setattr(status_label, 'text', '')) # Example delay
         pass # Or just leave the error message for a bit
    elif not window_modified and status_label:
         status_label.text = "" # Clear if selection failed entirely

# GUI setup

def on_config_select(widget):
    global config  # Use the global config variable
    try:
        if widget.value not in config_names:
            return
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
        # Re-enable buttons after applying
        if apply_button: apply_button.enabled = True
        if select_window_button: select_window_button.enabled = True
        if config_dropdown: config_dropdown.enabled = True
        if status_label: status_label.text = "" # Clear status label

    except Exception as e:
        if widget.value not in config_names:
            return
        print(f"Config selection error: {e}")
        import traceback
        traceback.print_exc()


def apply_settings(widget):
    global config, app

    selected_config = config_files[config_names.index(config_dropdown.value)]
    config = load_config(selected_config)
    if config:
        apply_configured_windows(config)
        # Re-enable buttons after applying
        apply_button.enabled = True
        select_window_button.enabled = True
        toggle_button.enabled = True
        config_dropdown.enabled = True
        status_label.text = "" # Clear status label
        if topmost_windows:
            toggle_button.enabled = True
        else:
            toggle_button.enabled = False        

        update_always_on_top_status()

def cancel_settings(widget):
    global waiting_for_window_selection, status_label
    global apply_button, select_window_button, toggle_button, config_dropdown

    if waiting_for_window_selection:
        waiting_for_window_selection = False

    reset_all_managed_windows()
    apply_button.enabled = True
    select_window_button.enabled = True
    toggle_button.enabled = True
    config_dropdown.enabled = True
    status_label.text = "" # Clear status label

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
        status += "Enabled" if is_enabled else "Mixed"
    
    try:
        setattr(always_on_top_status, 'text', status)
    except:
        pass

def draw_screen_layout(canvas, context, w, h, config, existing_windows, missing_windows):
    # Draws the screen layout on the canvas based on the configuration.
    global screen_width, screen_height
    try:
        # Setup background and border
        with context.Fill(color='#303030') as fill:
            fill.rect(0, 0, w, h)
        with context.Stroke(color='black', line_width=2) as stroke:
            stroke.rect(2, 2, w-2, h-2)
        
        # Draw Windows taskbar (48px high) at the bottom
        taskbar_height = 48
        scaled_taskbar_height = (taskbar_height / screen_height) * h
        with context.Fill(color='#222222') as fill:
            fill.rect(0, h - scaled_taskbar_height, w, scaled_taskbar_height)
        with context.Stroke(color='#222222', line_width=1) as stroke:
            stroke.rect(0, h - scaled_taskbar_height, w, scaled_taskbar_height)
        
        if not config or not config.sections():
            return
            
        # Get screen dimensions and calculate usable area
        padding = 1
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
                
                # Scale to canvas to fit the screen
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
        with context.Fill(color="blue" if not always_on_top else 'green') as fill:
            fill.rect(x, y, w, h)
        with context.Stroke(color='darkblue' if not always_on_top else 'darkgreen') as stroke:
            stroke.rect(x, y, w, h)
        
        # Text layout parameters
        text_x = int(x + 5)
        text_y = int(y + 15)
        line_height = 20
        
        # Format text same as previous settings display
        pos_text = f"X {real_x}, Y {real_y}"
        size_text = f"{real_w} x {real_h}"
        
        # Draw text lines
        text_lines = [
            title,
            f"Position:\n{pos_text}",
            f"\nSize:\n{size_text}",
            f"\n\nAlways-on-top:\n{'Yes' if always_on_top else 'No'}"
        ]
        
        my_font = toga.Font(SANS_SERIF, 10, weight=BOLD)
        # Draw lines
        for i, line in enumerate(text_lines):
            y_pos = text_y + (i * line_height)
            with context.Fill(color="#FFFFFF") as fill:
                fill.write_text(line, text_x, y_pos, font=my_font)
        
        # Add missing text if window is not found
        if not window_exists:
            with context.Fill(color='red') as fill:
                fill.write_text("\n\n\n\n\nMissing", text_x, text_y + (len(text_lines) * line_height), font=my_font)
        
    except Exception as e:
        print(f"Error drawing window box: {str(e)}")
        import traceback
        traceback.print_exc()

def create_gui(app):
    global box, config_dropdown, toggle_button, always_on_top_status, config_files, config_names, screen_canvas, screen_width, screen_height, apply_button, select_window_button, status_label
    get_screen_resolution()

    try:
        # Define main container
        box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        # Create header section
        header_box = toga.Box(style=Pack(direction=COLUMN, margin=5))
        
        # Define dropdown
        config_files, config_names = list_config_files()
        if not config_files:
            print("No configuration files found")
            config_files = ['No config found']
            config_names = ['No config found']
            
        config_dropdown = toga.Selection(
            items=config_names, 
            on_change=lambda widget: on_config_select(widget),
            style=Pack(flex=1, margin=(0,0,5,0))
        )
        header_box.add(config_dropdown)
        
        screen_info = f"Screen: {screen_width} x {screen_height}"
        screen_dimensions_label = toga.Label(
            screen_info,
            style=Pack(margin=(0,0,5,0))
        )
        header_box.add(screen_dimensions_label)

        # Define canvas
        canvas_height = 200
        canvas_width = int(canvas_height * (screen_width/screen_height))
        screen_canvas = toga.Canvas(
            style=Pack(
                margin=5,
                height=canvas_height,
                width=canvas_width,
                flex=1,
                background_color="#303030"
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
        button_box = toga.Box(style=Pack(direction='row', margin=5))

        # Define status labels
        always_on_top_status = toga.Label(
            "Always-on-Top: Disabled",
            style=Pack(margin=5)
        )
        status_label = toga.Label(
            "",
            style=Pack(margin=5) # Add some top padding
        )

        # Define Select Window button
        select_window_button = toga.Button(
            'Select Window',
            on_press=start_window_selection, # We'll define this function next
            style=Pack(margin=2, flex=1)
        )

        # Define buttons
        apply_button = toga.Button('Apply config', on_press=apply_settings, style=Pack(margin=2, flex=1))
        cancel_button = toga.Button('Cancel/reset settings', on_press=cancel_settings, style=Pack(margin=2, flex=1))
        toggle_button = toga.Button('Toggle Always-on-Top', on_press=toggle_always_on_top_button, style=Pack(margin=2), enabled=False)

        button_box.add(apply_button)
        button_box.add(cancel_button)
        button_box.add(select_window_button)

        # Define Create Config button
        create_config_button = toga.Button(
            'Create Config',
            on_press=create_config, # We'll define this function next
            style=Pack(margin=2, flex=1)
        )
        button_box.add(create_config_button)

        # Define open config folder button
        def open_config_folder(widget):
            try:
                os.startfile(config_dir)  # Open the configuration directory
            except Exception as e:
                print(f"Error opening config folder: {e}")
                import traceback
                traceback.print_exc()
        
        open_config_button = toga.Button('Open Config Folder', on_press=open_config_folder, style=Pack(margin=2, flex=1))
        button_box.add(open_config_button)

        # Define restart as admin button
        admin_status = is_running_as_admin()
        restart_as_admin_button = toga.Button(
            'Restart as Admin',
            on_press=restart_as_admin,
            style=Pack(margin=2, flex=1),
            enabled=not admin_status
        )
        button_box.add(restart_as_admin_button)

        # Add admin indicator label
        admin_label = toga.Label(
            "Running with Administrator permissions" if admin_status else "Running with User permissions",
            style=Pack(margin=5, color="green" if admin_status else "red")
        )
        box.add(admin_label)

        # Assemble the layout
        box.add(header_box)
        box.add(screen_canvas)
        box.add(button_box)
        box.add(always_on_top_status)
        box.add(toggle_button)

        # Configure window
        app.main_window.content = box
        app.main_window.size = (700, 400)
        app.main_window.position = (
            screen_width - app.main_window.size[0],
            screen_height / 2
        )

        # Set initial value and trigger selection
        config_dropdown.value = detect_and_set_default_config()
        on_config_select(config_dropdown)
        
        update_always_on_top_status() # Initialize the label
        return box

    except Exception as e:
        print(f"Error creating GUI: {e}")
        import traceback
        traceback.print_exc()
        return None

def detect_and_set_default_config():
    global config_files, config_names

    # Iterate through all configuration files
    for config_file in config_files:
        config = load_config(config_file)
        if not config:
            continue

        for section in config.sections():
            if config[section].getboolean("always_on_top", fallback=False):
                all_titles = gw.getAllTitles()
                cleaned_section = clean_title(section)

                for title in all_titles:
                    cleaned_title = clean_title(title)
                    if cleaned_section in cleaned_title:
                        return config_names[config_files.index(config_file)]

    return config_names[0]

def show_menu():
    global app
    app = toga.App('Window Positioner', 'Window Positioner', startup=create_gui)
    return app

def create_config(widget):
    #print("Create config button pressed")
    # Create a new window
    create_config_window = toga.Window(title="Create Config")

    # Get the main window position
    main_window_x = app.main_window.position[0]
    main_window_y = app.main_window.position[1]

    # Set the new window position
    create_config_window.position = (main_window_x + 20, main_window_y + 20)

    # Get a list of currently open windows
    all_titles = gw.getAllTitles()
    window_list = [title for title in all_titles if title]

    # Create a main box to hold all window elements
    main_box = toga.Box(style=Pack(direction=COLUMN, margin=10))

    # Store the selected windows in a global variable
    global selected_windows_for_config
    selected_windows_for_config = []

    # Create a box to hold the switches
    switch_box = toga.Box(style=Pack(direction=COLUMN, margin=5))

    # Create a switch for each window
    window_switches = {}
    for window_title in window_list:
        switch = toga.Switch(window_title, style=Pack(margin=5))
        window_switches[window_title] = switch
        switch_box.add(switch)

    # Add the switch box to the main box
    main_box.add(switch_box)

    # Add a button to confirm the selection
    def confirm_selection(widget):
        selected_windows = []
        for window_title, switch in window_switches.items():
            if switch.value:
                selected_windows.append(window_title)

        if len(selected_windows) > 4:
            print("You can only select up to 4 windows.")
            return

        # Store the selected windows in a global variable
        global selected_windows_for_config
        selected_windows_for_config = selected_windows

        # Create a main box to hold all window settings
        settings_box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        # Create a box for each selected window
        window_settings = {}
        for window_title in selected_windows:
            app_box = toga.Box(style=Pack(direction=COLUMN, margin=5))
            window_settings[window_title] = app_box

            # Add a label to display the window title
            title_input = toga.TextInput(value=clean_title(window_title), style=Pack(margin=5))
            app_box.add(title_input)

            # Get the position and size of the window
            try:
                w_position = gw.getWindowsWithTitle(window_title)[0].topleft
                w_size = gw.getWindowsWithTitle(window_title)[0].size
            except IndexError:
                w_position = (0, 0)
                w_size = (100, 100)

            window_box = toga.Box(style=Pack(direction=ROW, margin=5))
            
            # Add input fields to adjust the size and position
            size_label = toga.Label("Size (width, height):", style=Pack(margin=5))
            size_input = toga.TextInput(value=f'{w_size.width},{w_size.height}', style=Pack(margin=0))
            window_box.add(size_label)
            window_box.add(size_input)

            position_label = toga.Label("Position (x, y):", style=Pack(margin=5))
            position_input = toga.TextInput(value=f'{w_position.x},{w_position.y}', style=Pack(margin=0))
            window_box.add(position_label)
            window_box.add(position_input)

            # Add switches to toggle AOT and titlebar settings
            aot_switch = toga.Switch("Always on Top", style=Pack(margin=5))
            window_box.add(aot_switch)

            titlebar_switch = toga.Switch("Titlebar", style=Pack(margin=5), value=True)
            window_box.add(titlebar_switch)

            app_box.add(window_box)

            # Add the window box to the main box
            settings_box.add(app_box)

        def save_config(widget):
            # Get the values from the input fields and switches for each selected window
            config_data = {}
            for i, window_title in enumerate(selected_windows_for_config):
                window_box = window_settings[window_title]
                title_input = window_box.children[0]
                size_input = window_box.children[2]
                position_input = window_box.children[4]
                aot_switch = window_box.children[5]
                titlebar_switch = window_box.children[6]

                config_data[title_input.value] = {
                    "size": size_input.value,
                    "position": position_input.value,
                    "always_on_top": aot_switch.value,
                    "titlebar": titlebar_switch.value,
                }

            # Create a new ConfigParser object
            config = configparser.ConfigParser()

            # Add a section for each selected window to the ConfigParser object
            for window_title, settings in config_data.items():
                config.add_section(window_title)
                config.set(window_title, "size", str(settings["size"]))
                config.set(window_title, "position", str(settings["position"]))
                config.set(window_title, "always_on_top", str(settings["always_on_top"]))
                config.set(window_title, "titlebar", str(settings["titlebar"]))

            filepath = filename_input.value
            if not filepath:
                async def show_dialog():
                    dlg = toga.ErrorDialog("Error", "Config name cannot be empty.")
                    await dlg._show(create_config_window)
                asyncio.ensure_future(show_dialog())
                return
            if not filepath.startswith("config_"):
                filepath = "config_" + filepath
            if not filepath.endswith(".ini"):
                filepath += ".ini"

            # Save the configuration to the new file
            try:
                with open(os.path.join(config_dir, filepath), "w") as configfile:
                    config.write(configfile)
                print(f"Configuration saved to {filepath}")
            except Exception as e:
                print(f"Error saving configuration: {e}")
            
            # Refresh the config dropdown
            global config_files, config_names
            config_files, config_names = list_config_files()
            config_dropdown.items = config_names

            create_config_window.close()

        # Add filename input
        filename_label = toga.Label("Enter config name:", style=Pack(margin=5))
        filename_input = toga.TextInput(style=Pack(margin=5))
        settings_box.add(filename_label)
        settings_box.add(filename_input)
        
        # Add save button
        save_button = toga.Button("Save Config", on_press=save_config, style=Pack(margin=5))
        settings_box.add(save_button)

        # Set the content of the create_config_window to the main box
        create_config_window.content = settings_box

    confirm_button = toga.Button("Confirm Selection", on_press=confirm_selection, style=Pack(margin=5))

    # Add the button to the main box
    main_box.add(confirm_button)

    # Add the Box to the new window
    create_config_window.content = main_box

    # Show the new window
    create_config_window.show()

# End of GUI setup

async def is_window_being_dragged():
    # Detects if a window is being dragged by checking if the left mouse button is pressed and the mouse position is changing.
    global is_dragging
    # Check if the left mouse button is pressed
    if win32api.GetAsyncKeyState(0x01):
        initial_pos = win32gui.GetCursorPos()
        await asyncio.sleep(0.1)  # Small delay to check for movement
        current_pos = win32gui.GetCursorPos()

        # If the mouse position has changed, assume a drag is happening
        if initial_pos != current_pos:
            is_dragging = True
            return True
    is_dragging = False
    return False

def is_running_as_admin():
    if sys.platform == "win32":
        import ctypes
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False
    return False

def main():
    # First check for config_ files
    config_files, _ = list_config_files()
    
    if not config_files:
        show_menu().main_loop()
        return
    
    show_menu().main_loop()

if __name__ == "__main__":
    main()
