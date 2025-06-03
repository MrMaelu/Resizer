import win32gui
import win32con
import win32api
import pygetwindow as gw
import time
import threading

class WindowManager:
    def __init__(self):
        self.managed_windows = []
        self.topmost_windows = []
        self.selecting = False
        self.selected_window = None

    def set_always_on_top(self, hwnd, enable):
        try:
            # Get window title and use pygetwindow to get the handle
            window_title = win32gui.GetWindowText(hwnd)
            window = gw.getWindowsWithTitle(window_title)[0]
            hwnd = window._hWnd

            # Set window position
            flag = win32con.HWND_TOPMOST if enable else win32con.HWND_NOTOPMOST
            win32gui.SetWindowPos(
                hwnd, 
                flag,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOOWNERZORDER
            )

            # Update tracking list
            if enable and hwnd not in self.topmost_windows:
                self.topmost_windows.append(hwnd)
                self.managed_windows.append(hwnd)  # Add to managed windows like original
            elif not enable and hwnd in self.topmost_windows:
                self.topmost_windows.remove(hwnd)

            return True

        except Exception as e:
            print(f"Error setting always on top for hwnd: {hwnd}, enable: {enable}, error: {e}")
            return False

    def get_window_at_cursor(self):
        try:
            cursor_pos = win32gui.GetCursorPos()
            # Get window at cursor position
            hwnd = win32gui.WindowFromPoint(cursor_pos)
            
            if hwnd:
                # Get the root/parent window handle
                root_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
                if root_hwnd:
                    # Get and clean the root window title
                    title = self.clean_title(win32gui.GetWindowText(root_hwnd))
                    if title:
                        # Try to get the window directly through pygetwindow
                        windows = gw.getWindowsWithTitle(title)
                        if windows:
                            return windows[0]._hWnd
                        else:
                            # If not found by title, return the root window handle
                            return root_hwnd
            return None
        except Exception as e:
            print(f"Error getting window at cursor: {e}")
            import traceback
            traceback.print_exc()
            return None

    def start_window_selection(self):
        self.selecting = True
        self.selected_window = None
        # Start selection in a separate thread
        thread = threading.Thread(target=self._window_selection_loop)
        thread.daemon = True
        thread.start()
        return thread

    def _window_selection_loop(self):
        try:
            while self.selecting:
                # Check for left mouse button press
                if win32api.GetAsyncKeyState(0x01) < 0:  # VK_LBUTTON = 0x01
                    hwnd = self.get_window_at_cursor()
                    if hwnd:
                        window_title = win32gui.GetWindowText(hwnd)
                        print(f"Selected window: {window_title} (handle: {hwnd})")
                        
                        if self.set_always_on_top(hwnd, True):
                            print(f"Set window '{window_title}' as always on top")
                        else:
                            print(f"Failed to set window '{window_title}' as always on top")
                        
                        self.selected_window = hwnd
                        self.selecting = False
                        break
                time.sleep(0.05)  # Reduced sleep time for better responsiveness
        except Exception as e:
            print(f"Error in selection loop: {e}")
            import traceback
            traceback.print_exc()
            self.selecting = False

    def stop_window_selection(self):
        self.selecting = False
        return self.selected_window

    def get_base_title(self, title):
        try:
            if not title:
                return ""
                
            # Special cases for known applications
            lower_title = title.lower()
            
            # Visual Studio Code
            if "visual studio code" in lower_title or " - visual studio code" in lower_title:
                return "Visual Studio Code"
            
            # Discord
            if "discord" in lower_title:
                return "Discord"
                
            # Microsoft Edge
            if "microsoft" in lower_title and "edge" in lower_title:
                return "Microsoft Edge"
                
            # Opera
            if "opera" in lower_title or "speed dial" in lower_title:
                return "Opera"
            
            return title
                
        except Exception as e:
            print(f"Error getting base title: {e}")
            return title

    def clean_title(self, title):
        try:
            if not title:
                return ""
            
            # Remove RTL and LTR marks and other special characters including zero-width spaces
            cleaned = (
                title.replace('\u200e', '')  # Left-to-Right Mark
                     .replace('\u200f', '')  # Right-to-Left Mark
                     .replace('\u200b', '')  # Zero Width Space
                     .replace('\u200c', '')  # Zero Width Non-Joiner
                     .replace('\u200d', '')  # Zero Width Joiner
                     .replace('\u202a', '')  # Left-to-Right Embedding
                     .replace('\u202b', '')  # Right-to-Left Embedding
                     .replace('\u202c', '')  # Pop Directional Formatting
            )
            
            # Special handling for Edge
            if "microsoft" in cleaned.lower() and "edge" in cleaned.lower():
                # Look for the Edge part in any segment
                parts = cleaned.split(' - ')
                for part in parts:
                    if "microsoft edge" in part.lower():
                        return "Microsoft Edge"
                # Fallback if not found in parts
                return "Microsoft Edge"
            
            return self.get_base_title(cleaned)
            
        except Exception as e:
            print(f"Error cleaning title: {e}")
            print(f"Original title: {title}")
            print(f"Title bytes: {title.encode('unicode_escape')}")  # Debug Unicode
            return title or ""

    def title_matches(self, window_title, config_title):
        try:
            if not window_title or not config_title:
                return False
                
            # Get base application names
            window_base = self.clean_title(window_title)
            config_base = config_title
            
            # Direct comparison of base application names
            return window_base.lower() == config_base.lower()
                
        except Exception as e:
            print(f"Error matching titles: {e}")
            return False

    def apply_config(self, config):
        try:
            # Reset any currently managed windows
            self.reset_managed_windows()
            
            # Apply configuration to matching windows
            for section in config.sections():
                # Get window settings
                pos = config[section].get("position")
                size = config[section].get("size")
                always_on_top = config[section].getboolean("always_on_top", False)
                titlebar = config[section].getboolean("titlebar", True)
                
                print(f"Looking for window: {section}")  # Debug output
                
                # Find matching windows
                for window in gw.getAllWindows():
                    if window.title and self.title_matches(window.title, section):
                        hwnd = window._hWnd
                        print(f"Found matching window: {window.title}")  # Debug output
                        
                        # Apply settings
                        if always_on_top:
                            self.set_always_on_top(hwnd, True)
                        if not titlebar:
                            self.remove_titlebar(hwnd)
                        if pos:
                            x, y = map(int, pos.split(','))
                            window.moveTo(x, y)
                        if size:
                            w, h = map(int, size.split(','))
                            window.resizeTo(w, h)
                        
                        # Add to managed windows list
                        if hwnd not in self.managed_windows:
                            self.managed_windows.append(hwnd)
                        
            return True
        except Exception as e:
            print(f"Error applying config: {e}")
            import traceback
            traceback.print_exc()
            return False

    def reset_managed_windows(self):
        for hwnd in self.managed_windows[:]:
            try:
                # Remove always-on-top
                if hwnd in self.topmost_windows:
                    self.set_always_on_top(hwnd, False)
                    self.topmost_windows.remove(hwnd)
            
            except Exception as e:
                print(f"Error resetting window {hwnd}: {e}")
            
        # Clear managed windows list
        self.managed_windows.clear()

    def remove_titlebar(self, hwnd):
        try:
            # Get current window style
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            
            # Remove titlebar-related styles
            new_style = style & ~(
                win32con.WS_CAPTION |      # Title bar
                win32con.WS_THICKFRAME |   # Sizing border
                win32con.WS_MINIMIZEBOX |  # Minimize button
                win32con.WS_MAXIMIZEBOX |  # Maximize button
                win32con.WS_SYSMENU        # System menu
            )
            
            # Apply new style
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, new_style)
            
            # Force window to redraw
            win32gui.SetWindowPos(
                hwnd, None, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | 
                win32con.SWP_NOSIZE | 
                win32con.SWP_NOZORDER |
                win32con.SWP_FRAMECHANGED
            )
            return True
            
        except Exception as e:
            print(f"Error removing titlebar: {e}")
            return False

    def restore_titlebar(self, hwnd):
        try:
            # Get current window style
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            
            # Add back titlebar-related styles
            new_style = style | (
                win32con.WS_CAPTION |      # Title bar
                win32con.WS_THICKFRAME |   # Sizing border
                win32con.WS_MINIMIZEBOX |  # Minimize button
                win32con.WS_MAXIMIZEBOX |  # Maximize button
                win32con.WS_SYSMENU        # System menu
            )
            
            # Apply new style
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, new_style)
            
            # Force window to redraw
            win32gui.SetWindowPos(
                hwnd, None, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | 
                win32con.SWP_NOSIZE | 
                win32con.SWP_NOZORDER |
                win32con.SWP_FRAMECHANGED
            )
            return True
            
        except Exception as e:
            print(f"Error restoring titlebar: {e}")
            return False
