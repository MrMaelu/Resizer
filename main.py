import os
import sys
from ctypes import windll
import tkinter as tk
import tkinter.messagebox as messagebox

# Local imports
from config_manager import ConfigManager
from window_manager import WindowManager
from constants import UIConstants
from layout import TkGUIManager
from utils import WindowInfo

class ApplicationState:
    def __init__(self):
        # Core references
        self._app = None
        
        # Initialize managers first
        self.window_manager = None
        self.config_manager = None
        
        # System state
        self.is_admin = False
        
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

    def apply_settings(self):
        selected_config = self.config_files[self.config_names.index(self.app.combo_box.var.get())]

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
            
            self.update_always_on_top_status()

    def reset_settings(self):
        # Reset any existing windows first
        self.window_manager.reset_all_windows()
    
    def toggle_always_on_top(self):
        for hwnd in self.window_manager.topmost_windows:
            self.window_manager.toggle_always_on_top(hwnd)
        self.update_always_on_top_status()

    def update_always_on_top_status(self):
        try:
            status = self.window_manager.get_always_on_top_status()
            self.app.aot_label['text'] = status
        except Exception as e:
            print(f"Error updating always-on-top status: {e}")

    def open_config_folder(self):
        # Open the config folder in File Explorer
        if sys.platform == "win32":
            os.startfile(config_dir)

    def restart_as_admin(self):
        # Restart the application with admin privileges
        if sys.platform == "win32":
            params = " ".join([f'"{arg}"' for arg in sys.argv])
            print(f"Restarting with admin privileges: {params}")
            # ShellExecuteW returns >32 if successful
            rc = windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, params, None, 1
            )
            if rc > 32:
                os._exit(0)

    def create_config(self):
        state.app.create_config_ui(state.app.root,
            state.window_manager.get_all_window_titles(),
            state.config_manager.save_window_config,
            state.config_manager.collect_window_settings,
            state.update_config_list
        )

    def delete_config(self):
        current_name = state.app.combo_box.var.get().strip()
        if not current_name:
            messagebox.showerror("Error", "No config selected to delete.")
            return

        confirm = messagebox.askyesno("Confirm Delete", f"Delete config '{current_name}'?")
        if confirm:
            deleted = state.config_manager.delete_config(current_name)
            if deleted:
                state.update_config_list()
            else:
                messagebox.showerror("Error", f"Failed to delete '{current_name}'.")

    def on_mode_toggle(self=None, startup=False):
        state.app.toggle_compact(startup)
        state.compact = state.app.compact_mode
        state.config_manager.save_settings(state.compact)
        if state.app.compact_mode:
            state.update_managed_windows_list(state.config)
        else:
            existing_windows, missing_windows = state.window_manager.find_matching_windows(state.config)
            state.compute_window_layout(state.config, missing_windows)

    def theme(self):
        state.app.change_gui_theme()
        if state.app.compact_mode:
            state.update_managed_windows_list(state.config)
    
    def on_config_select(self, selected_value):
        if selected_value in state.config_names:
            idx = state.config_names.index(selected_value)
            selected_config = state.config_files[idx]
            loaded_config = state.config_manager.load_config(selected_config)
            state.config = self.config_manager.validate_and_repair_config(loaded_config)
            existing_windows, missing_windows = state.window_manager.find_matching_windows(state.config)
            if not state.app.compact_mode:
                state.compute_window_layout(state.config, missing_windows)
            else:
                state.update_managed_windows_list(state.config)

    def update_managed_windows_list(self, config):
        if not hasattr(state.app, 'managed_text'):
            state.app.setup_managed_text()  # Ensure widgets exist

        lines = []
        aot_lines = []
        if config:
            for section in config.sections():
                is_aot = config.getboolean(section, "always_on_top", fallback=False)
                title = f"* {section} *" if is_aot else section
                if len(title) > UIConstants.WINDOW_TITLE_MAX_LENGTH:
                    title = title[:UIConstants.WINDOW_TITLE_MAX_LENGTH] + "..."
                lines.append(title)
                aot_lines.append(is_aot)

        state.app.update_managed_text(lines, aot_lines)

    def compute_window_layout(self, config, missing_windows):
        positioned_windows = []

        if config:
            for section in config.sections():
                pos = config[section].get("position")
                size = config[section].get("size")
                
                if pos and size:
                    pos_x, pos_y = map(int, pos.split(','))
                    size_w, size_h = map(int, size.split(','))
                    always_on_top = config[section].get("always_on_top", "false").lower() == "true"
                    window_exists = section not in missing_windows
                    positioned_windows.append(WindowInfo(section, pos_x, pos_y, size_w, size_h, always_on_top, window_exists))

            state.app.set_layout_frame(state.screen_width, state.screen_height, positioned_windows)

    def update_config_list(self, config=None):
        state.config_files, state.config_names = state.config_manager.list_config_files()
        if state.config_files and state.config_names:
            state.app.combo_box.values = state.config_names
            state.app.combo_box.var.set(config or state.config_names[0])
            state.on_config_select(config or state.config_names[0])


def load_tk_GUI():
    root = tk.Tk()
    callbacks = {
        "apply_config": state.apply_settings,
        "reset_config": state.reset_settings,
        "create_config": state.create_config,
        "open_config_folder": state.open_config_folder,
        "restart_as_admin": state.restart_as_admin,
        "toggle_AOT": state.toggle_always_on_top,
        "config_selected": state.on_config_select,
        "toggle_compact": state.on_mode_toggle,
        "delete_config": state.delete_config,
        "theme": state.theme,
    }
    app = TkGUIManager(root, callbacks=callbacks, compact=state.compact, is_admin=state.is_admin)
    state.app = app
    
    state.app.compact_mode = state.compact
    
    # Get screen resolution
    state.screen_width = app.root.winfo_screenwidth()
    state.screen_height = app.root.winfo_screenheight()

    # Set GUI size and position
    x = (state.screen_width // 2) - (UIConstants.WINDOW_WIDTH // 2)
    y = (state.screen_height // 2) - (UIConstants.WINDOW_HEIGHT // 2)
    root.geometry(f"{UIConstants.WINDOW_WIDTH}x{UIConstants.WINDOW_HEIGHT}+{x}+{y}")

    # Update screen resolution label text
    app.resolution_label["text"] = f"{state.screen_width} x {state.screen_height}"

    # Set default config

    if state.compact: state.on_mode_toggle(startup=True)
    
    default_config = state.config_manager.detect_default_config(state.window_manager)
    
    state.update_config_list(default_config)
    
    state.app.root.mainloop()
    

if __name__ == "__main__":
    # Get application base path
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    # Set up managers
    state = ApplicationState()
    state.window_manager = WindowManager()
    state.config_manager = ConfigManager(base_path, state.window_manager)

    # Set config folder
    config_dir = os.path.join(base_path, "configs")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # Load settings
    settings_file = os.path.join(base_path, "settings.json")
    state.compact = state.config_manager.load_settings()

    # Check for admin rights
    try:
        state.is_admin = windll.shell32.IsUserAnAdmin()
    except:
        state.is_admin = False

    load_tk_GUI()

