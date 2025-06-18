import re
from dataclasses import dataclass

@dataclass
class WindowInfo:
    name: str
    pos_x: int
    pos_y: int
    width: int
    height: int
    always_on_top: bool
    exists: bool

def clean_window_title(title, sanitize=False):
    if not title:
        return ""
    
    # Basic cleaning
    title = re.sub(r'[^\x20-\x7E]', '', title)
    title = re.sub(r'\s+', ' ', title)
    title = title.strip().lower()
    
    if sanitize:
        # Additional cleaning for config files
        parts = re.split(r' [-—–] ', title)
        title = parts[-1].strip()
        title = re.sub(r'\s*\(.*\)$', '', title)
        title = re.sub(r'\s+\d+%$', '', title)
        title = re.sub(r'[<>:"/\\|?*\[\]]', '', title)
    
    return title.title()

def invert_hex_color(hex_color):
    # Remove '#' if present
    hex_color = hex_color.lstrip('#')
    # Split into RGB parts
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    # Invert each component
    r_inv = 255 - r
    g_inv = 255 - g
    b_inv = 255 - b

    # Format back to hex
    return f"#{r_inv:02X}{g_inv:02X}{b_inv:02X}"

def choose_color(color, approved_dark_themes, theme=None):
    return color if theme in approved_dark_themes else invert_hex_color(color)
