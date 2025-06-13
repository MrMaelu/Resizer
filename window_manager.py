import win32gui
import win32con
import traceback
import pygetwindow as gw
import win32api
import time
from utils import clean_window_title

class WindowManager:
    def __init__(self):
        self.managed_windows = []
        self.topmost_windows = set()
        self._window_states = {}

    def set_always_on_top(self, hwnd, enable):
        try:
            flag = win32con.HWND_TOPMOST if enable else win32con.HWND_NOTOPMOST
            win32gui.SetWindowPos(hwnd, flag, 0, 0, 0, 0, 
                                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | 
                                win32con.SWP_NOOWNERZORDER)
            
            if enable and hwnd not in self.topmost_windows:
                self.topmost_windows.add(hwnd)
            elif not enable and hwnd in self.topmost_windows:
                self.topmost_windows.remove(hwnd)
                
        except Exception as e:
            print(f"Error setting always on top for hwnd: {hwnd}, enable: {enable}, error: {e}")
            traceback.print_exc()

    def add_managed_window(self, hwnd):
        # Add a window to managed windows and store its initial state
        try:
            if hwnd not in self.managed_windows:
                self.managed_windows.append(hwnd)
                # Store initial window state
                self._window_states[hwnd] = self.get_window_metrics(hwnd)
        except Exception as e:
            print(f"Error adding managed window {hwnd}: {e}")
            traceback.print_exc()

    def remove_managed_window(self, hwnd):
        try:
            if hwnd in self.managed_windows:
                # Restore original state if available
                if hwnd in self._window_states:
                    original_state = self._window_states[hwnd]
                    self.set_window_position(hwnd, 
                                          original_state['position'][0],
                                          original_state['position'][1])
                    self.set_window_size(hwnd, 
                                       original_state['size'][0],
                                       original_state['size'][1])
                    
                    # Restore original window styles
                    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, 
                                         original_state['style'])
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, 
                                         original_state['exstyle'])
                    
                    del self._window_states[hwnd]
                
                self.managed_windows.remove(hwnd)
                if hwnd in self.topmost_windows:
                    self.topmost_windows.remove(hwnd)

        except Exception as e:
            print(f"Error removing managed window {hwnd}: {e}")
            traceback.print_exc()

    def reset_all_windows(self):
        # Reset all managed windows to their original state
        windows_to_reset = self.managed_windows.copy()  # Create a copy to avoid modification during iteration
        for hwnd in windows_to_reset:
            self.remove_managed_window(hwnd)

    def get_window_info(self, window_title):
        # Get window information by title
        try:
            window = gw.getWindowsWithTitle(window_title)
            if window and window[0]:
                window = window[0]
                # Sanitize the title before returning
                clean_title = clean_window_title(window_title, sanitize=True)
                return {
                    'hwnd': window._hWnd,
                    'title': clean_title,
                    'pos': (window.left, window.top),  # Fixed tuple syntax
                    'size': (window.width, window.height)  # Fixed tuple syntax
                }
        except Exception as e:
            print(f"Error getting window info: {e}")
        return None

    def get_always_on_top_status(self):
        # Get status of always-on-top windows
        count = 0
        if len(self.topmost_windows) == 0:
            return "AOT: None"
        else:
            for hwnd in self.topmost_windows:
                if (win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST) != 0:
                    count += 1

        return f"AOT: {count} window{'s' if count > 1 else ''}"

    def check_window_valid(self, hwnd):
        # Check if a window handle is still valid
        try:
            return win32gui.IsWindow(hwnd)
        except Exception:
            return False

    def cleanup_invalid_windows(self):
        # Remove any invalid windows from management
        try:
            invalid_windows = [hwnd for hwnd in self.managed_windows 
                             if not self.check_window_valid(hwnd)]
            
            for hwnd in invalid_windows:
                if hwnd in self._window_states:
                    del self._window_states[hwnd]
                if hwnd in self.topmost_windows:
                    self.topmost_windows.remove(hwnd)
                self.managed_windows.remove(hwnd)
                
            return len(invalid_windows)
        except Exception as e:
            print(f"Error cleaning up invalid windows: {e}")
            traceback.print_exc()
            return 0

    def set_window_position(self, hwnd, x, y):
        # Set window position with error handling
        try:
            # Get current window size
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            
            win32gui.SetWindowPos(hwnd, 0, x, y, width, height,
                                win32con.SWP_NOZORDER | win32con.SWP_NOSIZE)
            return True
        except Exception as e:
            print(f"Error setting window position for {hwnd}: {e}")
            traceback.print_exc()
            return False

    def set_window_size(self, hwnd, width, height):
        # Set window size with error handling
        try:
            # Get current position
            rect = win32gui.GetWindowRect(hwnd)
            x, y = rect[0], rect[1]
            
            win32gui.SetWindowPos(hwnd, 0, x, y, width, height,
                                win32con.SWP_NOZORDER | win32con.SWP_NOMOVE)
            return True
        except Exception as e:
            print(f"Error setting window size for {hwnd}: {e}")
            traceback.print_exc()
            return False

    def get_window_title(self, hwnd):
        # Get window title with error handling
        try:
            return win32gui.GetWindowText(hwnd)
        except Exception as e:
            print(f"Error getting window title for {hwnd}: {e}")
            return ""

    def is_window_visible(self, hwnd):
        # Check if window is visible with error handling
        try:
            return win32gui.IsWindowVisible(hwnd)
        except Exception:
            return False

    def get_window_metrics(self, hwnd):
        # Get comprehensive window metrics
        try:
            rect = win32gui.GetWindowRect(hwnd)
            return {
                'position': (rect[0], rect[1]),
                'size': (rect[2] - rect[0], rect[3] - rect[1]),
                'style': win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE),
                'exstyle': win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            }
        except Exception as e:
            print(f"Error getting window metrics: {e}")
            traceback.print_exc()
            return None

    def make_borderless(self, hwnd):
        # Remove titlebar and borders to create a borderless window
        try:
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            # Remove title bar, borders, and thick frame
            style &= ~(win32con.WS_CAPTION | win32con.WS_BORDER | win32con.WS_THICKFRAME)
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | 
                                win32con.SWP_FRAMECHANGED)
            return True
        except Exception as e:
            print(f"Error making window borderless for hwnd: {hwnd}, error: {e}")
            traceback.print_exc()
            return False

    def restore_window_frame(self, hwnd):
        # Restore titlebar and borders
        try:
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            # Restore title bar, borders, and thick frame
            style |= (win32con.WS_CAPTION | win32con.WS_BORDER | win32con.WS_THICKFRAME)
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | 
                                win32con.SWP_FRAMECHANGED | win32con.SWP_SHOWWINDOW)
            return True
        except Exception as e:
            print(f"Error restoring window frame for hwnd: {hwnd}, error: {e}")
            traceback.print_exc()
            return False

    def apply_window_config(self, config, hwnd):
        # Apply configuration settings to a window
        try:
            if not config:
                return False
            
            # Add window to managed windows first
            self.add_managed_window(hwnd)

            # Restore minimized window if needed
            window = gw.Window(hwnd)
            if window.isMinimized:
                self.restore_window(hwnd)

            # Handle dictionary config directly
            if isinstance(config, dict):
                # Apply position if specified
                if 'position' in config and config['position']:
                    try:
                        pos = eval(config['position']) if isinstance(config['position'], str) else config['position']
                        self.set_window_position(hwnd, pos[0], pos[1])
                    except Exception as e:
                        print(f"Error setting position: {e}")

                # Apply size if specified
                if 'size' in config and config['size']:
                    try:
                        size = eval(config['size']) if isinstance(config['size'], str) else config['size']
                        self.set_window_size(hwnd, size[0], size[1])
                    except Exception as e:
                        print(f"Error setting size: {e}")

                # Apply window state settings
                if 'always_on_top' in config:
                    self.set_always_on_top(hwnd, config['always_on_top'])

                if 'has_titlebar' in config:
                    if not config['has_titlebar']:
                        self.make_borderless(hwnd)
                    else:
                        self.restore_window_frame(hwnd)
                        
            # Handle ConfigParser config
            elif hasattr(config, 'sections'):
                window_title = self.get_window_title(hwnd)
                for section in config.sections():
                    if self._match_window_title(section, window_title):
                        position = config.get(section, 'position', fallback=None)
                        size = config.get(section, 'size', fallback=None)
                        always_on_top = config.getboolean(section, 'always_on_top', fallback=False)
                        has_titlebar = config.getboolean(section, 'has_titlebar', fallback=True)
                        
                        if position:
                            pos = eval(position)
                            self.set_window_position(hwnd, pos[0], pos[1])
                        if size:
                            dimensions = eval(size)
                            self.set_window_size(hwnd, dimensions[0], dimensions[1])
                        self.set_always_on_top(hwnd, always_on_top)
                        if not has_titlebar:
                            self.make_borderless(hwnd)
                        break

            return True
        except Exception as e:
            print(f"Error applying window config: {e}")
            traceback.print_exc()
            return False

    def _match_window_title(self, config_title, window_title):
        # Match window title with config section name
        config_title = config_title.lower().strip()
        window_title = window_title.lower().strip()
        return config_title in window_title

    def find_matching_windows(self, config):
        # Find all windows matching configuration sections
        matching_windows = []
        missing_windows = []
        
        try:
            if not config or len(config.sections()) == 0:
                return matching_windows, missing_windows

            all_titles = gw.getAllTitles()
            
            for section in config.sections():
                cleaned_section = clean_window_title(section)
                window_exists = False
                
                for title in all_titles:
                    if not title:
                        continue
                    cleaned_title = clean_window_title(title)
                    if cleaned_section in cleaned_title:
                        window = gw.getWindowsWithTitle(title)[0]
                        matching_windows.append({
                            'config_name': section,
                            'window': window,
                            'hwnd': window._hWnd
                        })
                        window_exists = True
                        break
                        
                if not window_exists:
                    missing_windows.append(section)
                    
            return matching_windows, missing_windows
        except Exception as e:
            print(f"Error finding matching windows: {e}")
            traceback.print_exc()
            return [], []

    def get_window_info_for_config(self, hwnd):
        # Get window information in config-friendly format
        try:
            window = gw.Window(hwnd)
            return {
                'title': win32gui.GetWindowText(hwnd),
                'position': window.topleft,
                'size': window.size,
                'always_on_top': hwnd in self.topmost_windows,
                'has_titlebar': bool(win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE) & win32con.WS_CAPTION)
            }
        except Exception as e:
            print(f"Error getting window info: {e}")
            traceback.print_exc()
            return None

    def find_window_by_title(self, title):
        # Find window by title (with partial matching)
        try:
            windows = gw.getWindowsWithTitle(title)
            return windows[0]._hWnd if windows else None
        except Exception as e:
            print(f"Error finding window: {e}")
            traceback.print_exc()
            return None

    def manage_selected_window(self, hwnd):
        # Manage a list of selected window handles
        try:
            if not hwnd or not win32gui.IsWindow(hwnd):
                return False
        
            self.add_managed_window(hwnd)
            self.set_always_on_top(hwnd, True)
            self.make_borderless(hwnd)
            return True
        
        except Exception as e:
            print(f"Error managing window {hwnd}: {e}")
            traceback.print_exc()
            return False
        
    def toggle_always_on_top(self, hwnd):
        # Toggle always-on-top state for a window
        try:
            if hwnd in self.topmost_windows:
                is_topmost = (win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST) != 0
                print(f"Window {hwnd} is currently {'topmost' if is_topmost else 'not topmost'}")
                flag = win32con.HWND_TOPMOST if not is_topmost else win32con.HWND_NOTOPMOST
                win32gui.SetWindowPos(hwnd, flag, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOOWNERZORDER)
            
        except Exception as e:
            print(f"Error toggling always-on-top: {e}")
            return False

    def listen_for_window_click(self, app_window_title):
        # Listen for window click and return clicked window handle
        try:
            # Get the HWND of Toga application window
            app_hwnd = self.find_window_by_title(app_window_title)
            
            while True:
                if win32api.GetAsyncKeyState(0x01) & 0x8000:
                    cursor_pos = win32gui.GetCursorPos()
                    hwnd_at_cursor = win32gui.WindowFromPoint(cursor_pos)
                    
                    if hwnd_at_cursor and hwnd_at_cursor != app_hwnd:
                        root_hwnd = win32gui.GetAncestor(hwnd_at_cursor, win32con.GA_ROOT)
                        if root_hwnd and root_hwnd != app_hwnd:
                            return root_hwnd
                
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error in window click detection: {e}")
            return None

    def get_all_window_titles(self):
        # Get a list of all visible window titles
        try:
            def enum_window_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title and not self._is_system_window(title):
                        windows.append(title)
                return True

            windows = []
            win32gui.EnumWindows(enum_window_callback, windows)
            return sorted(windows)
        except Exception as e:
            print(f"Error getting window titles: {e}")
            return []

    def _is_system_window(self, title):
        # Check if window is a system window that should be excluded
        system_windows = [
            "Program Manager",
            "Windows Input Experience",
            "Microsoft Text Input Application",
            "Settings",
            "Windows Shell Experience Host"
        ]
        return any(sys_win.lower() in title.lower() for sys_win in system_windows)

    def get_window_info(self, title):
        # Get position and size information for a window
        try:
            hwnd = win32gui.FindWindow(None, title)
            if not hwnd:
                return None

            rect = win32gui.GetWindowRect(hwnd)
            return {
                "position": (rect[0], rect[1]),
                "size": (rect[2] - rect[0], rect[3] - rect[1]),
                "title": title,
                "hwnd": hwnd
            }
        except Exception as e:
            print(f"Error getting window info: {e}")
            return None

