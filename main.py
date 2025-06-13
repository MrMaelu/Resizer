import os
import sys
import toga
from toga.style.pack import COLUMN, Pack, BOLD, SANS_SERIF
import asyncio
import threading
import ctypes
from config_manager import ConfigManager
from window_manager import WindowManager
from constants import UIConstants, Colors, Messages
from gui_manager import GUIManager

class ApplicationState:
    def __init__(self):
        # Core references
        self._app = None
        self.gui_manager = None
        
        # Initialize managers first
        self.window_manager = WindowManager()
        self.config_manager = None  # Will be set after base_path is defined
        
        # System state
        self.is_admin = is_running_as_admin()  # Add this line
        
        # UI state
        self.compact = False
        self.waiting_for_window_selection = False
        self.selected_window_hwnd = None
        
        # Screen info
        self.screen_width = 1920
        self.screen_height = 1080
        
        # Config state
        self.config_files = []
        self.config_names = []
        self.config = None
        
        # UI elements - initialized later by GUI manager
        self.status_label = None
        self.always_on_top_status = None
        self.config_dropdown = None
        self.apply_button = None
        self.select_window_button = None
        self.create_config_button = None
        self.open_config_button = None
        self.restart_as_admin_button = None
        self.toggle_compact_button = None
        self.toggle_button = None
        self.screen_canvas = None
        
    @property
    def app(self):
        return self._app

    @app.setter
    def app(self, value):
        self._app = value
        if self.gui_manager:
            self.gui_manager.app = value

    def start_window_selection(self, widget):
        self.waiting_for_window_selection = True
        self.status_label.text = Messages.CLICK_TARGET

        # Disable UI elements
        for element in [self.apply_button, self.select_window_button, 
                       self.toggle_button, self.config_dropdown]:
            if element:
                element.enabled = False

        # Reset existing windows
        self.window_manager.reset_all_windows()

        # Start click detection in separate thread
        click_thread = threading.Thread(
            target=lambda: self.handle_click_detection(app.formal_name),
            daemon=True
        )
        click_thread.start()

    def handle_click_detection(self, app_title):
        self.selected_window_hwnd = self.window_manager.listen_for_window_click(app_title)
        if self.selected_window_hwnd:
            app.loop.call_soon_threadsafe(self.handle_window_selection)
        
        self.waiting_for_window_selection = False

    def handle_window_selection(self):
        self.waiting_for_window_selection = False
        success = self.window_manager.manage_selected_window(self.selected_window_hwnd)
        self.update_ui_state(success)

    def update_ui_state(self, success):
        if success and self.status_label:
            window_info = self.window_manager.get_window_info_for_config(self.selected_window_hwnd)
            self.status_label.text = f"Applied to: '{window_info['title'][:30]}...'"
        else:
            self.status_label.text = Messages.WINDOW_SELECT_FAILED

        # Re-enable UI elements
        for element in [self.apply_button, self.select_window_button, self.config_dropdown]:
            if element:
                element.enabled = True
        if self.toggle_button:
            self.toggle_button.enabled = bool(self.window_manager.topmost_windows)

    def update_config_and_canvas(self, widget):
        try:
            if widget.value not in self.config_names:
                return
            selected_config = self.config_files[self.config_names.index(widget.value)]
            config = self.config_manager.load_config(selected_config)
            if not config:
                print(Messages.ERROR_NO_CONFIG)
                return

            existing_windows, missing_windows = self.window_manager.find_matching_windows(config)

            if not self.compact:
                # Update canvas with window layout
                def config_draw(context, w, h):
                    draw_screen_layout(self.screen_canvas, context, w, h, config, 
                                    existing_windows, missing_windows)

                self.screen_canvas.draw = config_draw
                config_draw(self.screen_canvas.context, 
                          self.screen_canvas.style.width,
                          self.screen_canvas.style.height)
                self.screen_canvas.refresh()

            # Re-enable buttons after applying
            if self.apply_button: self.apply_button.enabled = True
            if self.select_window_button: self.select_window_button.enabled = True
            if self.config_dropdown: self.config_dropdown.enabled = True
            if self.status_label: self.status_label.text = ""

        except Exception as e:
            if widget.value not in self.config_names:
                return
            print(f"Config selection error: {e}")

    def apply_settings(self, widget):
        selected_config = self.config_files[self.config_names.index(self.config_dropdown.value)]
        config = self.config_manager.load_config(selected_config)
        if config:
            # Find matching windows
            matching_windows, missing_windows = self.window_manager.find_matching_windows(config)
            
            # Reset any existing windows first
            self.window_manager.reset_all_windows()
            
            # Apply configuration to matching windows
            for match in matching_windows:
                try:
                    hwnd = match['hwnd']
                    section = match['config_name']
                    
                    # Get window settings from config
                    settings = {
                        'position': config.get(section, 'position', fallback=None),
                        'size': config.get(section, 'size', fallback=None),
                        'always_on_top': config.getboolean(section, 'always_on_top', fallback=False),
                        'has_titlebar': config.getboolean(section, 'titlebar', fallback=True)
                    }
                    
                    # Apply settings using window manager
                    self.window_manager.apply_window_config(settings, hwnd)
                    
                except Exception as e:
                    print(f"Error applying settings to window {match['config_name']}: {e}")
                    continue
            
            # Update UI state
            self.apply_button.enabled = True
            self.select_window_button.enabled = True
            self.toggle_button.enabled = True
            self.config_dropdown.enabled = True
            self.status_label.text = ""
            
            # Enable/disable toggle button based on whether there are any topmost windows
            self.toggle_button.enabled = bool(self.window_manager.topmost_windows)
            
            self.update_always_on_top_status()

    def cancel_settings(self, widget):
        if self.waiting_for_window_selection:
            self.waiting_for_window_selection = False

        self.window_manager.reset_all_windows()
        self.update_always_on_top_status()
        self.apply_button.enabled = True
        self.select_window_button.enabled = True
        self.toggle_button.enabled = True
        self.config_dropdown.enabled = True
        self.status_label.text = ""

    def toggle_always_on_top_button(self, widget):
        for hwnd in self.window_manager.topmost_windows:
            self.window_manager.toggle_always_on_top(hwnd)
        self.update_always_on_top_status()

    def update_always_on_top_status(self):
        try:
            status = self.window_manager.get_always_on_top_status()
            setattr(self.always_on_top_status, 'text', status)
        except Exception as e:
            print(f"Error updating always-on-top status: {e}")

    def toggle_compact_mode(self, widget, *args, **kwargs):
        # Toggle between compact and full mode
        try:
            if not self.app:
                print(Messages.ERROR_NO_APP)
                return

            # Toggle compact mode and save setting
            self.compact = not self.compact
            self.config_manager.save_settings(self.compact)
            
            if self.app.main_window:
                # Create and set new content
                new_content = self.gui_manager.create_gui()
                if new_content:
                    self.app.main_window.content = new_content
                    self.app._impl.create_menus()
                    
                    # Center window after content update
                    self.gui_manager.center_window()
                    
                    # Update window size
                    window_size = (
                        UIConstants.COMPACT_WIDTH,
                        UIConstants.COMPACT_HEIGHT
                    ) if self.compact else (
                        UIConstants.WINDOW_WIDTH,
                        UIConstants.WINDOW_HEIGHT
                    )
                    self.app.main_window.size = window_size
                    
                    # Restore config selection and update UI
                    if self.config_dropdown and self.config_dropdown.value:
                        self.gui_manager.on_config_select(self.config_dropdown)

        except Exception as e:
            print(f"Error toggling compact mode: {e}")

    def create_config(self, widget):
        # Disable main window controls while config window is open
        self.toggle_main_window_controls(False)
        
        def on_config_window_close(window):
            self.toggle_main_window_controls(True)
            return True

        create_config_window = toga.Window(
            title="Create Config", 
            size=(100, 100),
            resizable=False,
            on_close=on_config_window_close
        )

        create_config_window.position = (
            self.app.main_window.position[0] + 50,
            self.app.main_window.position[1] + 50
        )

        def save_configuration(config_name, window_data):
            # Save configuration and update UI
            if self.config_manager.save_window_config(config_name, window_data):
                # Refresh config dropdown
                self.config_files, self.config_names = self.config_manager.list_config_files()
                self.config_dropdown.items = self.config_names
                create_config_window.close()
                return True
            return False

        def create_settings_ui(window_data):
            # Create settings UI for selected windows
            settings_box = toga.Box(style=Pack(direction=COLUMN, margin=10, width=200))
            modified_settings = {}  # Store modified settings
            
            # Create window settings boxes
            for title, settings in window_data.items():
                window_box = state.config_manager.create_window_settings_box(title, settings)
                settings_box.add(window_box)
                settings_box.add(toga.Divider(style=Pack(margin=0)))

                # Store initial settings
                modified_settings[title] = {
                    'position': settings.get('position', ''),
                    'size': settings.get('size', ''),
                    'always_on_top': settings.get('always_on_top', False),
                    'titlebar': settings.get('titlebar', True)
                }

                # Add change handlers
                def on_setting_change(widget, title=title, setting_type=None):
                    if title not in modified_settings:
                        return

                    if setting_type == 'position':
                        modified_settings[title]['position'] = widget.value
                    elif setting_type == 'size':
                        modified_settings[title]['size'] = widget.value
                    elif setting_type == 'always_on_top':
                        modified_settings[title]['always_on_top'] = widget.value
                    elif setting_type == 'titlebar':
                        modified_settings[title]['titlebar'] = widget.value

                window_box.position_input.on_change = lambda w, t=title: on_setting_change(w, t, 'position')
                window_box.size_input.on_change = lambda w, t=title: on_setting_change(w, t, 'size')
                window_box.always_on_top_switch.on_change = lambda w, t=title: on_setting_change(w, t, 'always_on_top')
                window_box.titlebar_switch.on_change = lambda w, t=title: on_setting_change(w, t, 'titlebar')

            # Add save controls
            filename_box = toga.Box(style=Pack(direction=COLUMN, margin=UIConstants.MARGIN))
            filename_box.add(toga.Label(
                "Config name:",
                style=Pack(margin=UIConstants.MARGIN)
            ))
            filename_input = toga.TextInput(
                style=Pack(margin=UIConstants.MARGIN)
            )
            filename_box.add(filename_input)
            settings_box.add(filename_box)

            # Create save button
            settings_box.add(toga.Button(
                "Save Config",
                on_press=lambda w: save_configuration(filename_input.value, modified_settings),
                style=Pack(margin=UIConstants.MARGIN)
            ))

            create_config_window.content = settings_box

            # Calculate centered position that ensures window stays on screen
            window_x = self.app.main_window.position[0] + 50
            window_y = max(0, min(self.screen_height - create_config_window.size[1] - 80,
                          self.app.main_window.position[1] + 50))

            create_config_window.position = (window_x, window_y)

            return settings_box

        def handle_window_selection(selected):
            # Handle window selection and update UI
            if len(selected) <= UIConstants.MAX_WINDOWS:
                window_data = {
                    title: self.config_manager.collect_window_settings(title)
                    for title in selected
                }
                create_config_window.content = create_settings_ui(window_data)
                create_config_window.size = (200, 300)

        # Show initial window selection
        window_selection = create_window_selection_ui(
            self.window_manager.get_all_window_titles(),
            handle_window_selection
        )
        
        create_config_window.content = window_selection
        create_config_window.show()

    def open_config_folder(self, widget):
        # Open the config folder in File Explorer
        if sys.platform == "win32":
            os.startfile(config_dir)

    def restart_as_admin(self, widget):
        # Restart the application with admin privileges
        if sys.platform == "win32":
            params = " ".join([f'"{arg}"' for arg in sys.argv])
            print(f"Restarting with admin privileges: {params}")
            # ShellExecuteW returns >32 if successful
            rc = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, params, None, 1
            )
            if rc > 32:
                os._exit(0)

    def create_window_selection_ui(self, window_titles, on_selection):
        # Create UI for window selection
        selection_box = toga.Box(style=Pack(direction=COLUMN, margin=10))
        
        # Add header
        selection_box.add(toga.Label(
            "Select windows (max 4):",
            style=Pack(margin=UIConstants.MARGIN)
        ))

        # Create switches for each window
        window_switches = {}
        for title in window_titles:
            switch = toga.Switch(
                title,
                style=Pack(margin=2)
            )
            window_switches[title] = switch
            selection_box.add(switch)

        def confirm_selection(widget):
            selected = [
                title for title, switch in window_switches.items() 
                if switch.value
            ]
            
            if len(selected) > UIConstants.MAX_WINDOWS:
                asyncio.ensure_future(
                    toga.ErrorDialog(
                        "Error",
                        Messages.ERROR_TOO_MANY_WINDOWS
                    )._show(widget.window)
                )
                return
                
            if not selected:
                asyncio.ensure_future(
                    toga.ErrorDialog(
                        "Error",
                        Messages.ERROR_NO_WINDOWS
                    )._show(widget.window)
                )
                return
                
            on_selection(selected)

        # Add confirm button
        selection_box.add(toga.Button(
            "Confirm Selection",
            on_press=confirm_selection,
            style=Pack(margin=UIConstants.MARGIN)
        ))
        
        return selection_box

    def toggle_main_window_controls(self, enabled=True):
        controls = [
            self.apply_button,
            self.config_dropdown,
            self.select_window_button,
            self.toggle_compact_button,
            self.toggle_button,
            self.create_config_button,
            self.open_config_button,
            self.restart_as_admin_button
        ]
        
        for control in controls:
            if control:
                control.enabled = enabled

def is_running_as_admin():
    # Check if the script is running with admin privileges
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

config_dir = os.path.join(base_path, "configs")
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

settings_file = os.path.join(base_path, "settings.json")

state = ApplicationState()

# GUI setup

def draw_screen_layout(canvas, context, w, h, config, existing_windows, missing_windows):
    # Draws the screen layout on the canvas based on the configuration.
    try:
        # Setup background and border
        with context.Fill(color='black') as fill:
            fill.rect(0, 0, w, h)
        with context.Stroke(color='black', line_width=2) as stroke:
            stroke.rect(2, 2, w-2, h-2)
        
        # Draw Windows taskbar (48px high) at the bottom
        taskbar_height = UIConstants.TASKBAR_HEIGHT
        scaled_taskbar_height = (taskbar_height / state.screen_height) * h
        with context.Fill(color=Colors.TASKBAR) as fill:
            fill.rect(0, h - scaled_taskbar_height, w, scaled_taskbar_height)
        with context.Stroke(color=Colors.WINDOW_BORDER, line_width=1) as stroke:
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
                window_exists = section not in missing_windows
                
                # Scale to canvas to fit the screen
                scaled_x = (pos_x / state.screen_width) * usable_width + padding
                scaled_y = (pos_y / state.screen_height) * usable_height + padding
                scaled_w = (size_w / state.screen_width) * usable_width
                scaled_h = (size_h / state.screen_height) * usable_height
                
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
                    real_x = int(current_x * state.screen_width / usable_width)
                    real_y = int(current_y * state.screen_height / usable_height)
                    real_w = int(window_width * state.screen_width / usable_width)
                    real_h = int(window_height * state.screen_height / usable_height)
                    
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

def draw_window_box(context, title, x, y, w, h, real_x, real_y, real_w, real_h, always_on_top, window_exists):
    try:
        # Draw box
        with context.Fill(color=Colors.WINDOW_NORMAL if not always_on_top else Colors.WINDOW_ALWAYS_ON_TOP) as fill:
            fill.rect(x, y, w, h)
        with context.Stroke(color=Colors.WINDOW_BORDER) as stroke:
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
            with context.Fill(color=Colors.TEXT_NORMAL) as fill:
                fill.write_text(line, text_x, y_pos, font=my_font)
        
        # Add missing text if window is not found
        if not window_exists:
            with context.Fill(color=Colors.TEXT_ERROR) as fill:
                fill.write_text("\n\n\n\n\nMissing", text_x, text_y + (len(text_lines) * line_height), font=my_font)
        
    except Exception as e:
        print(f"Error drawing window box: {str(e)}")

def create_gui(app):
    try:
        # Update screen dimensions
        state.screen_width = app.screens[0].size[0]
        state.screen_height = app.screens[0].size[1]
        
        # Load config files
        state.config_files, state.config_names = state.config_manager.list_config_files()
        
        # Create main GUI content
        main_box = state.gui_manager.create_gui()
        if not main_box:
            raise Exception("Failed to create GUI content")
        
        state.app.main_window.size = (
            UIConstants.COMPACT_WIDTH if state.compact else UIConstants.WINDOW_WIDTH,
            UIConstants.COMPACT_HEIGHT if state.compact else UIConstants.WINDOW_HEIGHT
        )

        # Center the main window
        state.gui_manager.center_window()

        # Set default config if available
        if state.config_files and state.config_names:
            default_config = state.config_manager.detect_default_config(state.window_manager)
            if state.config_dropdown and default_config:
                state.config_dropdown.value = default_config
                state.gui_manager.on_config_select(state.config_dropdown)
        
        return main_box
        
    except Exception as e:
        print(f"Error in create_gui: {e}")
        import traceback
        traceback.print_exc()
        return toga.Box(style=Pack(direction=COLUMN))

def create_window_selection_ui(window_titles, on_selection):
    # Create UI for window selection
    selection_box = toga.Box(style=Pack(direction=COLUMN, margin=10))
    
    # Add header
    selection_box.add(toga.Label(
        "Select windows (max 4):",
        style=Pack(margin=UIConstants.MARGIN)
    ))

    # Create switches for each window
    window_switches = {}
    for title in window_titles:
        switch = toga.Switch(
            title,
            style=Pack(margin=2)
        )
        window_switches[title] = switch
        selection_box.add(switch)

    def confirm_selection(widget):
        selected = [
            title for title, switch in window_switches.items() 
            if switch.value
        ]
        
        if len(selected) > UIConstants.MAX_WINDOWS:
            asyncio.ensure_future(
                toga.ErrorDialog(
                    "Error",
                    Messages.ERROR_TOO_MANY_WINDOWS
                )._show(widget.window)
            )
            return
            
        if not selected:
            asyncio.ensure_future(
                toga.ErrorDialog(
                    "Error",
                    Messages.ERROR_NO_WINDOWS
                )._show(widget.window)
            )
            return
            
        on_selection(selected)

    # Add confirm button
    selection_box.add(toga.Button(
        "Confirm Selection",
        on_press=confirm_selection,
        style=Pack(margin=UIConstants.MARGIN)
    ))
    
    return selection_box

def main():
    try:
        # Create global state
        global state
        state = ApplicationState()
        
        # Set up base path and config manager
        base_path = os.path.dirname(os.path.abspath(__file__))
        state.config_manager = ConfigManager(base_path, state.window_manager)
        
        # Load compact mode setting before creating app
        compact_mode = state.config_manager.load_settings()
        state.compact = compact_mode
        
        # Create the app first
        app = toga.App(
            "Window Manager",
            "org.example.window-manager",
            startup=create_gui
        )
        
        # Initialize app reference
        state.app = app
        
        # Create GUI manager
        state.gui_manager = GUIManager(state, app)

        return app
        
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    app = main()
    if app:
        app.main_loop()
