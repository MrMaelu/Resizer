import pygetwindow as gw
import win32api
import win32gui
import win32con
import configparser
import os
import re
import toga
from toga.style.pack import COLUMN, Pack
import asyncio
from asyncio import Lock
import time
import threading

# Global lock for periodic checks
#periodic_check_lock = Lock()

is_dragging = False

"""
Window Positioner - Manage window layouts and apply manual overrides

This script provides a GUI to:
1. Load and apply window layout configurations (position, size, always-on-top, title bar)
   from '.ini' files.
2. Manually select any window to make it always-on-top and remove its title bar.

Features:
- Load and apply window configurations from 'config_*.ini' files.
- Visual preview of the selected configuration's layout.
- Periodic check to maintain the state of configured windows (when a config is applied).
- Manually select any window via button click to make it Always-on-Top and remove its title bar.
- Reset all applied settings (config or manual) using the 'Cancel/reset settings' button.
- Toggle Always-on-Top state specifically for windows managed by the *currently applied config*.
- Support for multiple configuration files.

Usage:
1. Place configuration files named 'config_<name>.ini' in the program directory.
2. Select a configuration from the dropdown menu to preview its layout.
3. Click 'Apply config' to activate the window layout defined in the selected config file.
   - A periodic check starts to maintain the state of these configured windows.
4. Click 'Select Window', then click on any target window on your screen.
   - This makes the selected window Always-on-Top and removes its title bar.
   - Entering selection mode stops any active configuration and periodic checks, and resets previously managed windows.
   - Applying a config or selecting a *new* window resets the previously *manually* selected one.
5. Click 'Cancel/reset settings':
   - If in 'Select Window' mode, it cancels the selection process.
   - It resets *all* windows currently managed (by config or manual selection) to their default state (Always-on-Top removed, title bar restored).
   - It re-enables all buttons.
6. Use 'Toggle Always-on-Top' to change the state of windows managed by the *currently applied config*. (Button is enabled only when a config with always-on-top windows is active).

Configuration Format (config_*.ini):
[Window Title]
position = x,y              # Window position (optional)
size = width,height         # Window size (optional)
always_on_top = true/false  # Set always-on-top state (optional, default false)
titlebar = true/false       # Keep title bar (optional, default true)

Example:
[Microsoft Edge]
position = 0,0
size = 1760,1400
always_on_top = true
titlebar = false

Notes:
- Windows without position/size in config will be auto-arranged based on screen size.
- Window titles in config are matched partially and case-insensitively against open windows.
"""

# globals
config = None
screen_width = 0
screen_height = 0
selected_window_button = None
status_label = None
waiting_for_window_selection = False
selected_window_hwnd = None

def get_screen_resolution():
    global screen_width, screen_height
#    max_screen_height = 0
    if screen_width == 0:
        for screen in app.screens:
            screen_width += screen.size[0]
        screen_height = app.screens[0].size[1]

def list_config_files():
    config_files = [f for f in os.listdir() if f.startswith("config_") and f.endswith(".ini")]
    config_files.sort()
    config_names = [f[7:-4] for f in config_files]
    return config_files, config_names

def load_config(config_path):
    config = configparser.ConfigParser()
    try:
        if os.path.exists(config_path):
            config.read(config_path)
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
            print(f"Added hwnd {hwnd} to topmost_windows")
        elif not enable and hwnd in topmost_windows:
            topmost_windows.remove(hwnd)
            print(f"Removed hwnd {hwnd} from topmost_windows")
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
            print(f"Restored titlebar for hwnd: {hwnd}")
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
    global waiting_for_window_selection, status_label, app#, periodic_check_lock
    global apply_button, select_window_button, toggle_button, config_dropdown

    waiting_for_window_selection = True
    status_label.text = "Click on the target window..."

    # Disable buttons while selecting
    apply_button.enabled = False
    select_window_button.enabled = False
    toggle_button.enabled = False
    config_dropdown.enabled = False

    # Stop periodic check if running
    #if hasattr(app, 'periodic_check_task') and app.periodic_check_task and not app.periodic_check_task.done():
    #    app.periodic_check_task.cancel()
        # Ensure the lock is released if the task was cancelled mid-operation
    #    if periodic_check_lock.locked():
    #         periodic_check_lock.release()

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

#    for hwnd in topmost_windows:
#        try:
#            always_on_top = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST
#            if always_on_top:
#                set_always_on_top(hwnd, False)
#        except Exception as e:
#            print("Failed to toggle always-on-top. Window might be closed.")

    # Stop the periodic check
    #if hasattr(app, 'periodic_check_task') and app.periodic_check_task:
    #    app.periodic_check_task.cancel()

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
            print(f"Window selected: '{selected_window_name}' (HWND: {selected_window_hwnd})")

            # --- Apply modifications ---
            print(f"Applying Always on Top to {selected_window_hwnd}")
            set_always_on_top(selected_window_hwnd, True)
            # Note: set_always_on_top adds to topmost_windows, which might be confusing
            # as this window isn't managed by a config. We might need to adjust reset logic later if needed.

            print(f"Removing titlebar from {selected_window_hwnd}")
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

async def periodic_check_windows_exist():
    return
    global periodic_check_lock, config, is_dragging

    while True:
        await asyncio.sleep(5)  # Wait 5 seconds before starting the next check
        async with periodic_check_lock:  # Ensure only one check runs at a time
            try:
                if not config:
                    print("No config applied. Stopping periodic check.")
                    break

                # Skip the check if a window is being dragged
                if await is_window_being_dragged():
                    continue

                # Check windows' existence and update their status
                existing_windows, missing_windows = check_windows_exist(config)
                update_window_status(config, existing_windows, missing_windows)

                # Check and fix always-on-top status
                for hwnd in topmost_windows:
                    if not win32gui.IsWindow(hwnd):
                        topmost_windows.remove(hwnd)
                        continue

                    always_on_top = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST
                    for section in config.sections():
                        if clean_title(section) in clean_title(win32gui.GetWindowText(hwnd)):
                            expected_status = config[section].getboolean("always_on_top", fallback=False)
                            if always_on_top != expected_status:
                                set_always_on_top(hwnd, expected_status)
            except Exception as e:
                print(f"Error during periodic check: {e}")

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

        # Start the periodic check for the applied config
        #if hasattr(app, 'periodic_check_task') and app.periodic_check_task:
        #    app.periodic_check_task.cancel()  # Cancel any existing periodic check
        #loop = asyncio.get_event_loop()
        #app.periodic_check_task = loop.create_task(periodic_check_windows_exist())

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
        with context.Fill(color='white') as fill:
            fill.rect(0, 0, w, h)
        with context.Stroke(color='black', line_width=2) as stroke:
            stroke.rect(5, 5, w-10, h-10)
        
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
        with context.Fill(color='lightblue' if not always_on_top else 'lightgreen') as fill:
            fill.rect(x, y, w, h)
        with context.Stroke(color='blue' if not always_on_top else 'green') as stroke:
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
            f"Position: {pos_text}",
            f"Size: {size_text}",
            f"Always-on-top: {'Yes' if always_on_top else 'No'}"
        ]
        
        # Draw lines
        for i, line in enumerate(text_lines):
            y_pos = text_y + (i * line_height)
            with context.Fill(color='rgba(0, 0, 0, 1)') as fill:
                fill.write_text(line, text_x, y_pos)
        
        # Add missing text if window is not found
        if not window_exists:
            with context.Fill(color='red') as fill:
                fill.write_text("\nMissing", text_x, text_y + (len(text_lines) * line_height))
        
    except Exception as e:
        print(f"Error drawing window box: {str(e)}")
        import traceback
        traceback.print_exc()

def create_gui(app):
    global box, config_dropdown, toggle_button, always_on_top_status, config_files, config_names, screen_canvas, screen_width, screen_height, apply_button, select_window_button, status_label
    get_screen_resolution()

    try:
        # Define main container
        box = toga.Box(style=Pack(direction=COLUMN, padding=10))

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

        # Define canvas
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

        # Define status labels
        always_on_top_status = toga.Label(
            "Always-on-Top: Disabled",
            style=Pack(padding=5)
        )
        status_label = toga.Label(
            "",
            style=Pack(padding=5) # Add some top padding
        )

        # Define Select Window button
        select_window_button = toga.Button(
            'Select Window',
            on_press=start_window_selection, # We'll define this function next
            style=Pack(padding=2, flex=1)
        )

        # Define buttons
        apply_button = toga.Button('Apply config', on_press=apply_settings, style=Pack(padding=2, flex=1))
        cancel_button = toga.Button('Cancel/reset settings', on_press=cancel_settings, style=Pack(padding=2, flex=1))
        toggle_button = toga.Button('Toggle Always-on-Top', on_press=toggle_always_on_top_button, style=Pack(padding=2), enabled=False)

        button_box.add(apply_button)
        button_box.add(cancel_button)
        button_box.add(select_window_button)

        # Assemble the layout
        box.add(header_box)
        box.add(screen_canvas)
        box.add(button_box)
        box.add(status_label)
        box.add(always_on_top_status)
        box.add(toggle_button)

        # Configure window
        app.main_window.content = box
        app.main_window.size = (700, 400)
        app.main_window.position = (
            screen_width - app.main_window.size[0],
            screen_height / 2
            # (screen_width // 2) - (app.main_window.size[0] // 2),
            # (screen_height // 2) - (app.main_window.size[1] // 2)
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

def main():
    # First check for config_ files
    config_files, _ = list_config_files()
    
    if not config_files:
        show_menu().main_loop()
        return
    
    show_menu().main_loop()

if __name__ == "__main__":
    main()
