class UIConstants:
    # Window dimensions
    WINDOW_WIDTH = 850
    WINDOW_HEIGHT = 480
    COMPACT_WIDTH = 180
    COMPACT_HEIGHT = 400
    BUTTON_WIDTH = 100
    COMPACT_BUTTON_WIDTH = 80
    CANVAS_HEIGHT = 240
    TASKBAR_HEIGHT = 48
    MAX_WINDOWS = 4
    WINDOW_TITLE_MAX_LENGTH = 24
    
    # UI element sizes
    MARGIN = (2,2,2,2)  # (top, right, bottom, left)
    PADDING = 0
    LINE_HEIGHT = 20
    FONT_SIZE = 8
    MANAGED_WINDOWS_WIDTH = 165
    MANAGED_WINDOWS_HEIGHT = (FONT_SIZE + 12) * MAX_WINDOWS
    CONFIG_DROPDOWN_WIDTH = 250
    LABEL_WIDTH = 60

    # Layout constants
    DEFAULT_ALIGN = 'center'  # Valid values: 'left', 'center', 'right'
    DEFAULT_DIRECTION = 'column'  # Valid values: 'row', 'column'

class Colors:
    # Background colors
    BACKGROUND = "#202020"
    TASKBAR = "#666666"
    
    # Window colors
    WINDOW_NORMAL = "#404040"
    WINDOW_ALWAYS_ON_TOP = "#508050"
    WINDOW_BORDER = "#050505"
    DIM_BORDER = "#555555"
    
    # Text colors
    TEXT_NORMAL = "#FFFFFF"
    TEXT_ERROR = "#FFFF00"
    TEXT_ALWAYS_ON_TOP = "#50A050"
    TEXT_DIM = "#555555"

    # Add these for darker backgrounds
    WINDOW_NORMAL_DARK = "#2A2A2A"
    WINDOW_ALWAYS_ON_TOP_DARK = "#3A3A3A"
    WINDOW_MISSING_DARK = "#3F1F1F"

    # Status colors
    ADMIN_ENABLED = "green"
    ADMIN_DISABLED = "red"

class Messages:
    # Status messages
    CLICK_TARGET = "Click on the target window..."
    WINDOW_SELECT_FAILED = "Window selection failed or cancelled."
    ALWAYS_ON_TOP_DISABLED = "AOT: None"
    SELECT_CONFIG = "Select a configuration"
    
    # Error messages
    ERROR_TOO_MANY_WINDOWS = f"Please select {UIConstants.MAX_WINDOWS} or fewer windows"
    ERROR_NO_WINDOWS = "Please select at least one window"
    ERROR_NO_APP = "Error: Application reference not set"
    ERROR_TOGGLE_COMPACT = "Error toggling compact mode: {}"
    ERROR_GUI_CREATION = "Error creating GUI: {}"
    ERROR_NO_CONFIG = "No config found"

class WindowStyles:
    TITLE_BAR_COLOR = '#000000'
    TITLE_TEXT_COLOR = '#FFFFFF'
    BORDER_COLOR = '#101010'

class Fonts:
    TEXT_NORMAL = ("Segoe UI", 10, "normal")
    TEXT_BOLD = ("Segoe UI", 10, "bold")

class Themes:
    APPROVED_DARK_THEMES = (
        'clam',
    )
    
    APPROVED_LIGHT_THEMES = (
        'default',
    )
