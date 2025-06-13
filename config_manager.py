import os
import configparser
import json
import traceback
import win32gui
import win32con
import pygetwindow as gw
import toga
from toga.style.pack import Pack, COLUMN, ROW
from constants import UIConstants
from utils import clean_window_title

class ConfigManager:
    def __init__(self, base_path, window_manager=None):
        print(f"Initializing ConfigManager with base_path: {base_path}")
        self.base_path = base_path
        self.config_dir = os.path.join(base_path, "configs")
        self.settings_file = os.path.join(base_path, "settings.json")
        self.window_manager = window_manager
        
        # Create config directory if it doesn't exist
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            print(f"Created config directory: {self.config_dir}")
    
        print("ConfigManager initialized")

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
        # Save window configuration to file
        try:
            if not config_name:
                return False

            config = configparser.ConfigParser()
            
            for title, settings in window_data.items():
                section_name = settings.get('name', clean_window_title(title, sanitize=True))
                
                config[section_name] = {
                    'position': str(settings.get('position', '0,0')),
                    'size': str(settings.get('size', '100,100')),
                    'always_on_top': str(settings.get('always_on_top', False)).lower(),
                    'titlebar': str(settings.get('titlebar', True)).lower()
                }

            config_path = os.path.join(self.config_dir, f"config_{config_name}.ini")
            with open(config_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)

            return True

        except Exception as e:
            print(f"Error saving window config: {e}")
            traceback.print_exc()
            return False

    def create_window_settings_box(self, title, settings):
        # Create a box with settings controls for a window
        window_box = toga.Box(style=Pack(direction=COLUMN, margin=5))
        
        # Store initial values for reset
        initial_values = {
            'name': settings.get('name', clean_window_title(title, sanitize=True)),
            'position': settings.get('position', '0,0'),
            'size': settings.get('size', '100,100'),
            'always_on_top': settings.get('always_on_top', 'false') == 'true',
            'titlebar': settings.get('titlebar', 'true') == 'true'
        }
        
        # Add title with editable name
        title_box = toga.Box(style=Pack(direction=ROW, margin=0))
        title_box.add(toga.Label('Name:', style=Pack(margin=(5,0,5,0), width=UIConstants.LABEL_WIDTH)))
        name_input = toga.TextInput(
            value=settings.get('name', clean_window_title(title, sanitize=True)),
            style=Pack(margin=2, width=130)
        )
        title_box.add(name_input)
        window_box.add(title_box)
        
        # Create position input
        pos_box = toga.Box(style=Pack(direction=ROW, margin=0))
        pos_box.add(toga.Label('Position:', style=Pack(margin=(5,0,5,0), width=UIConstants.LABEL_WIDTH)))
        position_input = toga.TextInput(
            value=settings.get('position', '0,0'),
            style=Pack(margin=2, width=60)
        )
        pos_box.add(position_input)
        window_box.add(pos_box)
        
        # Create size input
        size_box = toga.Box(style=Pack(direction=ROW, margin=0))
        size_box.add(toga.Label('Size:', style=Pack(margin=(5,0,5,0), width=UIConstants.LABEL_WIDTH)))
        size_input = toga.TextInput(
            value=settings.get('size', '100,100'),
            style=Pack(margin=2, width=60)
        )
        size_box.add(size_input)
        window_box.add(size_box)
        
        # Create always-on-top switch with label as text
        aot_box = toga.Box(style=Pack(direction=ROW, margin=0))
        always_on_top_switch = toga.Switch(
            'Always on Top',  # Add text parameter
            value=initial_values['always_on_top'],
            style=Pack(margin=5)
        )
        aot_box.add(always_on_top_switch)
        window_box.add(aot_box)
        
        # Create titlebar switch with label as text
        titlebar_box = toga.Box(style=Pack(direction=ROW, margin=0))
        titlebar_switch = toga.Switch(
            'Show Titlebar',  # Add text parameter
            value=initial_values['titlebar'],
            style=Pack(margin=5)
        )
        titlebar_box.add(titlebar_switch)
        window_box.add(titlebar_box)
        
        # Add reset button
        def reset_values(widget):
            name_input.value = initial_values['name']
            position_input.value = initial_values['position']
            size_input.value = initial_values['size']
            always_on_top_switch.value = initial_values['always_on_top']
            titlebar_switch.value = initial_values['titlebar']
        
        button_box = toga.Box(style=Pack(direction=ROW, margin=0))
        reset_button = toga.Button(
            'Reset',
            on_press=reset_values,
            style=Pack(margin=0, width=UIConstants.BUTTON_WIDTH)
        )
        button_box.add(reset_button)
        window_box.add(button_box)
        
        # Store references and initial values
        window_box.name_input = name_input
        window_box.position_input = position_input
        window_box.size_input = size_input
        window_box.always_on_top_switch = always_on_top_switch
        window_box.titlebar_switch = titlebar_switch
        window_box.original_title = title
        window_box.initial_values = initial_values
        
        return window_box

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
