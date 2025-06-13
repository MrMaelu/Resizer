import toga
from toga.style.pack import COLUMN, Pack, BOLD, ROW
from constants import UIConstants, Colors, Messages

class GUIManager:
    def __init__(self, state, app):
        print("Initializing GUI Manager")
        self.state = state
        self.app = app
        self.box = None
        self.header_box = None
        self.button_box = None
        self.managed_windows_box = None
        
        # Create base style
        self.base_style = Pack(
            margin=UIConstants.MARGIN,
            width=UIConstants.BUTTON_WIDTH
        )
        
        self.compact_style = Pack(
            margin=UIConstants.MARGIN,
            width=UIConstants.BUTTON_WIDTH
        )

        # Initialize UI elements immediately
        self.initialize_ui_elements()

    def create_header(self):
        # Create the header section of the GUI
        self.header_box = toga.Box(style=Pack(direction=COLUMN, margin=UIConstants.MARGIN))
        
        # Screen info
        screen_info = f"Screen: {self.state.screen_width} x {self.state.screen_height}"
        screen_label = toga.Label(
            screen_info,
            style=Pack(margin=(0,0,5,0))
        )
        
        # Config dropdown
        self.state.config_dropdown = toga.Selection(
            items=self.state.config_names,
            on_change=self.on_config_select,
            style=Pack(margin=UIConstants.MARGIN, width=UIConstants.CONFIG_DROPDOWN_WIDTH),
            enabled=True
        )

        self.header_box.add(screen_label)
        self.header_box.add(self.state.config_dropdown)

        if self.state.compact:
            self.add_managed_windows_list()

        return self.header_box

    def create_button_bar(self):
        # Create the button section of the GUI
        try:
            # Create base container
            self.button_box = toga.Box(style=Pack(
                direction=COLUMN,
                margin=UIConstants.MARGIN,
                align_items=UIConstants.DEFAULT_ALIGN
            ))

            # Create button sections
            main_buttons = toga.Box(style=Pack(
                direction=COLUMN if self.state.compact else ROW,
                margin=UIConstants.MARGIN,
                align_items=UIConstants.DEFAULT_ALIGN
            ))

            self.initialize_ui_elements()

            # Add main operation buttons
            buttons_to_add = [
                (self.state.apply_button, 'Apply config'),
                (self.state.select_window_button, 'Select Window'),
                (self.state.create_config_button, 'Create Config'),
                (self.state.open_config_button, 'Config Folder'),
                (self.state.restart_as_admin_button, 'Restart as Admin'),
                (self.state.toggle_compact_button, 'Toggle Compact')
            ]

            for button, text in buttons_to_add:
                if button:
                    button.style = self.compact_style if self.state.compact else self.base_style
                    main_buttons.add(button)

            self.button_box.add(main_buttons)

            # Create always-on-top section
            aot_box = toga.Box(style=Pack(
                direction=COLUMN,
                margin=UIConstants.MARGIN,
                align_items=UIConstants.DEFAULT_ALIGN
            ))

            # Add status label
            if self.state.always_on_top_status:
                aot_box.add(self.state.always_on_top_status)

            # Add toggle button
            if self.state.toggle_button:
                self.state.toggle_button.style = self.compact_style if self.state.compact else self.base_style
                aot_box.add(self.state.toggle_button)

            self.button_box.add(aot_box)
            return self.button_box

        except Exception as e:
            print(f"Error creating button bar: {e}")
            import traceback
            traceback.print_exc()
            return None

    def create_canvas(self):
        # Create the canvas for window layout preview
        if not self.state.compact:
            canvas_height = UIConstants.CANVAS_HEIGHT
            canvas_width = int(canvas_height * (self.state.screen_width/self.state.screen_height))
            
            self.state.screen_canvas = toga.Canvas(
                style=Pack(
                    margin=UIConstants.MARGIN,
                    height=canvas_height,
                    width=canvas_width,
                    flex=1,
                    background_color=Colors.BACKGROUND
                )
            )
            
            self.set_initial_canvas_state()
            return self.state.screen_canvas
        return None

    def set_initial_canvas_state(self):
        # Set the initial canvas state
        def initial_draw(context, w, h):
            with context.Fill(color='black') as fill:
                fill.rect(0, 0, w, h)
            with context.Stroke(color='black', line_width=2) as stroke:
                stroke.rect(5, 5, w-10, h-10)
            context.write_text(Messages.SELECT_CONFIG, w/2 - 60, h/2)
            
        self.state.screen_canvas.draw = initial_draw
        initial_draw(self.state.screen_canvas.context, 
                    self.state.screen_canvas.style.width,
                    self.state.screen_canvas.style.height)
        self.state.screen_canvas.refresh()

    def add_managed_windows_list(self):
        # Add the managed windows list to the header
        managed_windows_label = toga.Label(
            "Managed Windows:",
            style=Pack(margin=UIConstants.MARGIN)
        )
        
        self.managed_windows_box = toga.Box(
            style=Pack(
                direction=COLUMN,
                margin=UIConstants.MARGIN,
                width=UIConstants.MANAGED_WINDOWS_WIDTH,
                height=UIConstants.MANAGED_WINDOWS_HEIGHT,
                background_color=Colors.BACKGROUND,
            )
        )
        
        self.header_box.add(managed_windows_label)
        self.header_box.add(self.managed_windows_box)

    def update_managed_windows_list(self, config):
        # Update the managed windows list display
        if not self.managed_windows_box:
            return

        # Clear existing labels
        for child in self.managed_windows_box.children[:]:
            self.managed_windows_box.remove(child)
        
        if config:
            for section in config.sections():
                is_aot = config.getboolean(section, "always_on_top", fallback=False)
                
                if len(section) > UIConstants.WINDOW_TITLE_MAX_LENGTH:
                    section = section[:UIConstants.WINDOW_TITLE_MAX_LENGTH] + "..."
                    
                window_label = toga.Label(
                    f"• {section}{' *' if is_aot else ''}",
                    style=Pack(
                        margin=(3,0,0,0),
                        height=20,
                        color=Colors.TEXT_ALWAYS_ON_TOP if is_aot else Colors.TEXT_NORMAL,
                        font_weight=BOLD
                    )
                )
                self.managed_windows_box.add(window_label)

    def create_gui(self):
        # Create the main GUI layout
        try:
            print("Creating main GUI box")
            self.box = toga.Box(style=Pack(
                direction=COLUMN,
                margin=UIConstants.MARGIN,
                align_items=UIConstants.DEFAULT_ALIGN
            ))

            # Create header
            print("Creating header")
            header = self.create_header()
            if header:
                self.box.add(header)
            
            # Only create canvas if not in compact mode
            if not self.state.compact:
                print("Creating canvas")
                canvas = self.create_canvas()
                if canvas:
                    self.box.add(canvas)
        
            # Create and add button bar
            print("Creating button bar")
            button_bar = self.create_button_bar()
            if button_bar:
                self.box.add(button_bar)

            print("GUI creation complete")
            return self.box

        except Exception as e:
            print(f"Error creating GUI: {e}")
            import traceback
            traceback.print_exc()
            return None

    def initialize_ui_elements(self):
        # Initialize all UI elements
        # Create base style
        style = Pack(margin=UIConstants.MARGIN, width=UIConstants.BUTTON_WIDTH)
        if self.state.compact:
            style.width = UIConstants.COMPACT_BUTTON_WIDTH

        # Initialize status labels first
        self.state.status_label = toga.Label(
            "",
            style=style
        )
        
        self.state.always_on_top_status = toga.Label(
            Messages.ALWAYS_ON_TOP_DISABLED,
            style=style
        )

        # Initialize all buttons with consistent style
        button_configs = [
            ('apply_button', 'Apply config', self.state.apply_settings, False),
            ('select_window_button', 'Select Window', self.state.start_window_selection, True),
            ('create_config_button', 'Create Config', self.state.create_config, True),
            ('open_config_button', 'Config Folder', self.state.open_config_folder, True),
            ('restart_as_admin_button', 'Restart as Admin', self.state.restart_as_admin, not self.state.is_admin),
            ('toggle_compact_button', 'Toggle Compact', self.state.toggle_compact_mode, True),
            ('toggle_button', 'Toggle Always-on-Top', self.state.toggle_always_on_top_button, False)
        ]

        for attr_name, text, handler, enabled in button_configs:
            button = toga.Button(
                text,
                on_press=handler,
                style=style,
                enabled=enabled
            )
            setattr(self.state, attr_name, button)

    def center_window(self):
        # Center the main window on screen
        if self.app and self.app.main_window:
            screen_width = self.app.screens[0].size[0]
            screen_height = self.app.screens[0].size[1]
            window_width = self.app.main_window.size[0]
            window_height = self.app.main_window.size[1]
            
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            
            self.app.main_window.position = (x, y)

    def on_config_select(self, widget):
        # Handle config selection changes
        self.state.update_config_and_canvas(widget)
        if self.state.compact:
            selected_config = self.state.config_files[
                self.state.config_names.index(widget.value)]
            self.state.config = self.state.config_manager.load_config(selected_config)
            self.update_managed_windows_list(self.state.config)
