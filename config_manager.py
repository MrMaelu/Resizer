import re
import os
import configparser
import json
import traceback
import win32gui
import win32con
import pygetwindow as gw
from utils import clean_window_title

class ConfigManager:
    def __init__(self, base_path, window_manager=None):
        self.base_path = base_path
        self.config_dir = os.path.join(base_path, "configs")
        self.settings_file = os.path.join(base_path, "settings.json")
        self.window_manager = window_manager
        
        # Create config directory if it doesn't exist
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            print(f"Created config directory: {self.config_dir}")
    
    def list_config_files(self):
        # List all configuration files and their names
        config_files = [f for f in os.listdir(self.config_dir) 
                       if f.startswith("config_") and f.endswith(".ini")]
        config_files.sort()
        config_names = [f[7:-4] for f in config_files]
        return config_files, config_names

    def load_config(self, config_path):
        # Load a configuration file
        config = configparser.ConfigParser()
        try:
            full_path = os.path.join(self.config_dir, config_path)
            if os.path.exists(full_path):
                config.read(full_path)
                return config
            return None
        except Exception as e:
            print(f"Error loading config file {config_path}: {e}")
            traceback.print_exc()
            return None

    def load_settings(self):
        # Load application settings
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    return settings.get('compact', True)
                return True
            return True
        except Exception as e:
            print(f"Error loading settings: {e}")
            return True

    def save_settings(self, compact_mode):
        # Save application settings
        try:
            with open(self.settings_file, 'w') as f:
                json.dump({'compact': compact_mode}, f)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def detect_default_config(self, window_manager):
        # Detect and return the best default configuration
        config_files, config_names = self.list_config_files()
        
        for config_file in config_files:
            config = self.load_config(config_file)
            if not config:
                continue

            for section in config.sections():
                if config[section].getboolean("always_on_top", fallback=False):
                    all_titles = gw.getAllTitles()
                    cleaned_section = clean_window_title(section, sanitize=True)

                    for title in all_titles:
                        cleaned_title = clean_window_title(title, sanitize=True)
                        if cleaned_section in cleaned_title:
                            return config_names[config_files.index(config_file)]

        return config_names[0] if config_names else None

    def save_window_config(self, config_name, window_data):
        try:
            if not config_name:
                print("No config name provided")
                return False

            config_name = clean_window_title(config_name, sanitize=True)
            print(f"Saving config '{config_name}' with {len(window_data)} windows")

            config = configparser.ConfigParser()
            config.optionxform = str

            # Prepare and sort entries by x-position
            entries = []
            for title, settings in window_data.items():
                if title and title.strip():
                    section_name = settings.get('name') or title
                    section_name = clean_window_title(section_name, sanitize=True)
                    position = str(settings.get('position') or '0,0')
                    try:
                        x = int(position.split(',')[0])
                    except Exception:
                        x = 0
                    entries.append((x, section_name, settings))

            entries.sort(key=lambda x: x[0])  # Left to right by x-position

            # Add sorted entries to config
            for _, section_name, settings in entries:
                config[section_name] = {
                    'position': str(settings.get('position') or '0,0'),
                    'size': str(settings.get('size') or '100,100'),
                    'always_on_top': str(settings.get('always_on_top') or False).lower(),
                    'titlebar': str(settings.get('titlebar') or True).lower()
                }

            config = self.validate_and_repair_config(config)
            
            if not os.path.isdir(self.config_dir):
                print(f"Config directory {self.config_dir} does not exist.")
                return False

            config_path = os.path.join(self.config_dir, f"config_{config_name}.ini")
            print(f"Writing to file: {config_path}")

            with open(config_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)

            print("Config saved successfully")
            return True

        except Exception as e:
            print(f"Error saving window config: {e}")
            import traceback
            traceback.print_exc()
            return False

    def collect_window_settings(self, window_title):
        # Get settings for a window
        try:
            window = gw.getWindowsWithTitle(window_title)[0]
            # Get the current window state
            has_titlebar = bool(win32gui.GetWindowLong(window._hWnd, win32con.GWL_STYLE) 
                          & win32con.WS_CAPTION)
            is_topmost = (window._hWnd == win32gui.GetForegroundWindow())
            
            return {
                'position': f'{window.left},{window.top}',
                'size': f'{window.width},{window.height}',
                'always_on_top': str(is_topmost).lower(),
                'titlebar': str(has_titlebar).lower(),
                'original_title': window_title,
                'name': clean_window_title(window_title, sanitize=True)
            }
        except Exception as e:
            print(f"Error collecting window settings: {e}")
            return None

    def delete_config(self, name):
        try:
            path = os.path.join(self.config_dir, f"config_{name}.ini")
            if os.path.exists(path):
                os.remove(path)
                return True
        except Exception as e:
            print(f"Failed to delete config '{name}': {e}")
        return False

    def validate_and_repair_config(self, config):
        repaired_config = configparser.ConfigParser()
        repaired_config.optionxform = str

        for section in config.sections():
            if not section.strip() or section.upper() == "DEFAULT":
                continue
        
            valid_items = {}
            for key, value in config.items(section):
                if key == "position":
                    valid_items[key] = value if re.match(r"^\d+,\d+$", value) else "0,0"
                elif key == "size":
                    valid_items[key] = value if re.match(r"^\d+,\d+$", value) else "100,100"
                elif key in ("always_on_top", "titlebar"):
                    valid_items[key] = value.lower() if value.lower() in ("true", "false") else "false"
                elif value is not None and value.strip():
                    valid_items[key] = value.strip()
            
            if valid_items:
                repaired_config.add_section(section)
                for key, val in valid_items.items():
                    repaired_config.set(section, key, val)
            
        return repaired_config
