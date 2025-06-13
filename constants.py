class UIConstants:
    # Window dimensions
    WINDOW_WIDTH = 700
    WINDOW_HEIGHT = 250
    COMPACT_WIDTH = 180
    COMPACT_HEIGHT = 400
    BUTTON_WIDTH = 140
    COMPACT_BUTTON_WIDTH = 80
    CANVAS_HEIGHT = 240
    TASKBAR_HEIGHT = 48
    MAX_WINDOWS = 4
    WINDOW_TITLE_MAX_LENGTH = 20
    
    # UI element sizes
    MARGIN = (0,2,2,2)  # (top, right, bottom, left)
    PADDING = 2
    LINE_HEIGHT = 20
    FONT_SIZE = 8
    MANAGED_WINDOWS_WIDTH = 165
    MANAGED_WINDOWS_HEIGHT = (FONT_SIZE + 15) * MAX_WINDOWS
    CONFIG_DROPDOWN_WIDTH = 165
    LABEL_WIDTH = 60

    # Layout constants
    DEFAULT_ALIGN = 'center'  # Valid values: 'left', 'center', 'right'
    DEFAULT_DIRECTION = 'column'  # Valid values: 'row', 'column'

class Colors:
    # Background colors
    BACKGROUND = "#303030"
    TASKBAR = "#666666"
    
    # Window colors
    WINDOW_NORMAL = "#303030"
    WINDOW_ALWAYS_ON_TOP = "#508050"
    WINDOW_BORDER = "#050505"
    
    # Text colors
    TEXT_NORMAL = "#FFFFFF"
    TEXT_ERROR = "#ff5555"
    TEXT_ALWAYS_ON_TOP = "#50A050"
    
    # Status colors
    ADMIN_ENABLED = "green"
    ADMIN_DISABLED = "red"

class Messages:
    # Status messages
    CLICK_TARGET = "Click on the target window..."
    WINDOW_SELECT_FAILED = "Window selection failed or cancelled."
    ALWAYS_ON_TOP_DISABLED = "AOT: None"
    NO_CONFIG = "No config found"
    SELECT_CONFIG = "Select a configuration"
    
    # Error messages
    ERROR_TOO_MANY_WINDOWS = f"Please select {UIConstants.MAX_WINDOWS} or fewer windows"
    ERROR_NO_WINDOWS = "Please select at least one window"
    ERROR_NO_APP = "Error: Application reference not set"
    ERROR_TOGGLE_COMPACT = "Error toggling compact mode: {}"
    ERROR_GUI_CREATION = "Error creating GUI: {}"

