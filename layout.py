import re
import tkinter as tk
from tkinter import ttk, messagebox
import pywinstyles
from ctypes import windll
from typing import List

# Local imports
from utils import WindowInfo, clean_window_title, choose_color
from constants import UIConstants, Colors, Messages, WindowStyles, Fonts, Themes
from custom_widgets import CustomDropdown

class TkGUIManager:
    def __init__(self, root, callbacks=None):
        self.style = ttk.Style()
        self.available_themes = self.style.theme_names()
        self.theme_list = [
            theme for theme in self.available_themes
            if theme in Themes.APPROVED_DARK_THEMES
            or theme in Themes.APPROVED_LIGHT_THEMES
        ]

        self.theme = self.theme_list[0] or ''
        for theme in Themes.APPROVED_DARK_THEMES:
            if theme in self.theme_list:
                self.theme = theme

        self.root = root
        self.root.title("Window Manager")
        self.root.configure(bg=choose_color(Colors.BACKGROUND, Themes.APPROVED_DARK_THEMES, self.theme))

        self.default_font = Fonts.TEXT_NORMAL
        self.compact_mode = False
        self.canvas = None
        self.buttons_container = None
        self.managed_label = None
        self.managed_text = None

        self.callbacks = callbacks or {}

        self.apply_config = None
        self.create_config = None
        self.delete_config = None
        self.open_config_folder = None
        self.restart_as_admin = None
        self.toggle_AOT = None
        self.on_config_select = None
        self.on_mode_toggle = None

        self.setup_styles()
        self.create_layout()
        self.root.after(100, self.apply_titlebar_style)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use(self.theme)

        self.background = choose_color(Colors.BACKGROUND, Themes.APPROVED_DARK_THEMES, self.theme)
        self.text_normal = choose_color(Colors.TEXT_NORMAL, Themes.APPROVED_DARK_THEMES, self.theme)
        self.window_normal = choose_color(Colors.WINDOW_NORMAL, Themes.APPROVED_DARK_THEMES, self.theme)
        self.window_normal_dark = choose_color(Colors.WINDOW_NORMAL_DARK, Themes.APPROVED_DARK_THEMES, self.theme)
        self.window_border = choose_color(Colors.WINDOW_BORDER, Themes.APPROVED_DARK_THEMES, self.theme)
        self.taskbar = choose_color(Colors.TASKBAR, Themes.APPROVED_DARK_THEMES, self.theme)
        self.window_always_on_top = choose_color(Colors.WINDOW_ALWAYS_ON_TOP, Themes.APPROVED_DARK_THEMES, self.theme)
        self.text_error = choose_color(Colors.TEXT_ERROR, Themes.APPROVED_DARK_THEMES, self.theme)
        self.text_always_on_top = choose_color(Colors.TEXT_ALWAYS_ON_TOP, Themes.APPROVED_DARK_THEMES, self.theme)

        style.configure("TFrame", background=self.background)
        
        style.configure("TLabel",
            font=self.default_font,
            background=self.background,
            foreground=self.text_normal
        )
        
        style.configure("TButton",
            font=self.default_font,
            background=self.background,
            foreground=self.text_normal,
            activebackground=self.window_normal,
            activeforeground=self.text_normal
        )
        style.map("TButton", background=[('active', self.window_normal)], foreground=[('active', self.text_normal)])
        
        style.configure("TCombobox",
            font=self.default_font,
            background=self.background,
            foreground=self.text_normal,
            fieldbackground=self.background,
            borderwidth=1,
            selectbackground=self.window_normal,
            selectforeground=self.text_normal,
            padding=4
        )
        style.map("TCombobox", background=[('active', self.background)], fieldbackground=[('readonly', self.background)])

        style.configure("Custom.Vertical.TScrollbar",
            troughcolor=self.background,
            background=self.window_normal,
            arrowcolor=self.text_normal,
            relief="flat",
            bordercolor=self.background
        )

    def apply_titlebar_style(self):
        try:
            window = windll.user32.GetActiveWindow()
            pywinstyles.apply_style(window, 'dark' if self.theme in Themes.APPROVED_DARK_THEMES else 'normal')
            pywinstyles.change_header_color(window, color=choose_color(WindowStyles.TITLE_BAR_COLOR, Themes.APPROVED_DARK_THEMES, self.theme))
            pywinstyles.change_title_color(window, color=choose_color(WindowStyles.TITLE_TEXT_COLOR, Themes.APPROVED_DARK_THEMES, self.theme))
        except Exception as e:
            print(f"Error applying dark mode to titlebar: {e}")
    
    def create_layout(self):
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding=UIConstants.MARGIN)
        self.main_frame.configure(style="TFrame")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Header frame
        header_frame = ttk.Frame(self.main_frame, padding=UIConstants.MARGIN)
        header_frame.configure(style="TFrame")
        header_frame.pack(side=tk.TOP, fill=tk.X)

        # Managed windows (initially hidden)
        self.managed_frame = ttk.Frame(self.main_frame, padding=UIConstants.MARGIN)
        self.managed_frame.configure(style="TFrame")
        self.managed_frame.pack(side=tk.TOP, fill=tk.X)  # Pack here to fix order
        self.managed_frame.pack_forget()  # Hide it initially

        # Screen resolution label
        self.resolution_label = ttk.Label(header_frame, text="Screen: 0 x 0", padding=(0, 0, 5, 0))
        self.resolution_label.configure(style='TLabel')
        self.resolution_label.pack(side=tk.TOP, fill=tk.X)
        
        self.combo_box = CustomDropdown(header_frame, values=[], command=self.callbacks.get("config_selected", self.on_config_select))
        self.combo_box.pack(side=tk.LEFT, pady=UIConstants.MARGIN[2])
        self.combo_box.set_theme(self.theme)

        # Layout frame placeholder
        self.layout_container = ttk.Frame(self.main_frame, padding=UIConstants.MARGIN)
        self.layout_container.configure(style="TFrame")
        self.layout_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.layout_frame = None  # Will hold the ScreenLayoutFrame

        # Button section
        self.button_frame = ttk.Frame(self.main_frame, padding=UIConstants.MARGIN)
        self.button_frame.configure(style="TFrame")
        self.button_frame.pack(side=tk.TOP, fill=tk.X)

        # Main buttons frame
        main_buttons = ttk.Frame(self.button_frame, padding=UIConstants.MARGIN)
        main_buttons.configure(style="TFrame")
        main_buttons.pack(side=tk.TOP, fill=tk.X)

        # Add buttons with centered layout and adjusted width for symmetrical spacing
        buttons = [
            ("Apply config", self.callbacks.get("apply_config") or self.apply_config),
            ("Create Config", self.callbacks.get("create_config") or self.create_config),
            ("Delete Config", self.callbacks.get("delete_config") or self.delete_config),
            ("Config Folder", self.callbacks.get("open_config_folder") or self.open_config_folder),
            ("Restart as Admin", self.callbacks.get("restart_as_admin") or self.restart_as_admin),
            ("Toggle Compact", self.callbacks.get("toggle_compact") or self.toggle_compact),
            ("Theme", self.callbacks.get("theme") or self.change_gui_theme)
        ]

        self.buttons_container = ttk.Frame(main_buttons)
        self.buttons_container.pack(side=tk.TOP, fill=tk.X, expand=True, anchor=tk.CENTER)
        
        total_buttons_width = len(buttons) * 100
        self.buttons_container.configure(width=total_buttons_width)
        for name, command in buttons:
            btn = ttk.Button(self.buttons_container, text=name, command=command)
            btn.pack(side=tk.LEFT, padx=UIConstants.MARGIN[1], pady=UIConstants.MARGIN[2], fill=tk.X, expand=True)

        # AOT container
        aot_container = ttk.Frame(self.button_frame, padding=UIConstants.MARGIN)
        aot_container.configure(style="TFrame")
        aot_container.pack(side=tk.TOP, fill=tk.X, pady=(UIConstants.MARGIN[2], 0))

        # AOT status label
        aot_label_frame = ttk.Frame(aot_container, padding=UIConstants.MARGIN)
        aot_label_frame.configure(style="TFrame")
        aot_label_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, UIConstants.MARGIN[2]))
        self.aot_label = ttk.Label(aot_label_frame, text=Messages.ALWAYS_ON_TOP_DISABLED)
        self.aot_label.configure(style='TLabel')
        self.aot_label.pack(side=tk.TOP, anchor=tk.W)

        # AOT toggle button
        aot_button_frame = ttk.Frame(aot_container, padding=UIConstants.MARGIN)
        aot_button_frame.configure(style="TFrame")
        aot_button_frame.pack(side=tk.TOP, fill=tk.X, pady=(UIConstants.MARGIN[2], 0))
        aot_button = ttk.Button(aot_button_frame, text="Toggle AOT", width=20,
                                command=self.callbacks.get("toggle_AOT") or self.toggle_AOT)
        aot_button.pack(side=tk.TOP, anchor=tk.W)

    def setup_managed_text(self):
        # Create managed windows frame if not exists
        if not hasattr(self, 'managed_frame') or not self.managed_frame.winfo_ismapped():
            self.managed_frame.pack(before=self.button_frame, side=tk.TOP, fill=tk.X)
        
        if not self.managed_label:
            self.managed_label = ttk.Label(self.managed_frame, text="Managed windows:")
            self.managed_label.configure(style='TLabel')
            self.managed_label.pack(side=tk.TOP, anchor=tk.W)
        
        if not self.managed_text:
            self.managed_text = tk.Text(self.managed_frame,
                height=4,
                wrap=tk.WORD,
                background=self.background,
                foreground=self.text_normal,
                font=self.default_font
            )
            self.managed_text.pack(side=tk.TOP, fill=tk.X, expand=False)

    def clear_managed_text(self):
        if self.managed_text:
            self.managed_text.delete("1.0", tk.END)

    def update_managed_text(self, lines, aot_flags):
        self.managed_text.config(state=tk.NORMAL)
        self.managed_text.delete("1.0", tk.END)

        for i, line in enumerate(lines):
            if aot_flags[i]:
                # Insert line with green foreground tag
                self.managed_text.insert(tk.END, line + "\n", "aot")
            else:
                self.managed_text.insert(tk.END, line + "\n")

        self.managed_text.tag_config("aot", foreground=self.text_always_on_top, font=Fonts.TEXT_BOLD)
        self.managed_text.config(state=tk.DISABLED)

    def set_layout_frame(self, screen_width, screen_height, windows):
        # Clear old frame
        if self.layout_frame:
            self.layout_frame.destroy()

        # Create and pack new layout frame
        self.layout_frame = ScreenLayoutFrame(self.layout_container, screen_width, screen_height, windows, self.theme)
        self.layout_frame.pack(fill=tk.BOTH, expand=True)

    def scale_gui(self):
        if self.compact_mode:
            self.root.geometry(f"{UIConstants.COMPACT_WIDTH}x1")
            self.root.update_idletasks()
            height = self.root.winfo_reqheight()
            self.root.geometry(f"{UIConstants.COMPACT_WIDTH}x{height}")
        else:
            self.root.geometry(f"{UIConstants.WINDOW_WIDTH}x{UIConstants.WINDOW_HEIGHT}")
    
    def change_gui_theme(self):
        try:
            idx = (self.theme_list.index(self.theme) + 1) % len(self.theme_list)
            self.theme = self.theme_list[idx]

            # Redrawing GUI
            self.layout_frame.redraw(self.theme)
            self.setup_styles()
            self.combo_box.set_theme(self.theme)
            self.root.after(100, self.apply_titlebar_style)
            if self.compact_mode:
                if self.managed_label:
                    self.managed_label.destroy()
                    self.managed_label = None
                if self.managed_text:
                    self.managed_text.destroy()
                    self.managed_text = None
                self.managed_frame.pack_forget()
                self.setup_managed_text()
            
            self.scale_gui()
        except Exception as e:
            print("Theme change failed:", e)

    def toggle_compact(self):
        self.compact_mode = not self.compact_mode
        if self.compact_mode:
            if self.layout_container:
                self.layout_container.pack_forget()

            for child in self.buttons_container.winfo_children():
                child.pack_configure(side=tk.TOP, fill=tk.X)

            self.setup_managed_text()
            self.scale_gui()
        else:
            if self.layout_container:
                self.layout_container.pack(before=self.button_frame, side=tk.TOP, fill=tk.BOTH, expand=True)

            for child in self.buttons_container.winfo_children():
                if isinstance(child, ttk.Button):
                    child.pack_configure(side=tk.LEFT, fill=tk.X)

            if self.managed_label:
                self.managed_label.destroy()
                self.managed_label = None
            if self.managed_text:
                self.managed_text.destroy()
                self.managed_text = None

            self.managed_frame.pack_forget()
            self.scale_gui()

    def create_config_ui(self, parent, window_titles, save_callback, settings_callback, refresh_callback):
        parent.attributes('-disabled', True)

        def on_close():
            parent.attributes('-disabled', False)
            config_win.destroy()

        def confirm_selection():
            selected = [title for title, var in switches.items() if var.get()]
            if not selected:
                messagebox.showerror("Error", "No windows selected")
                return
            if len(selected) > UIConstants.MAX_WINDOWS:
                messagebox.showerror("Error", f"Select up to {UIConstants.MAX_WINDOWS} windows only")
                return
            show_config_settings(selected)

        def show_config_settings(selected_windows):
            for widget in config_win.winfo_children():
                widget.destroy()

            settings_frame = ttk.Frame(config_win)
            settings_frame.configure(style="TFrame")
            settings_frame.pack(fill='both', expand=True, padx=10, pady=10)

            settings_vars = {}
            for row, title in enumerate(selected_windows):
                values = settings_callback(title) or {}
                pos_var = tk.StringVar(value=values.get("position", "0,0"))
                size_var = tk.StringVar(value=values.get("size", "100,100"))
                aot_var = tk.BooleanVar(value=values.get("always_on_top", "false") == "true")
                titlebar_var = tk.BooleanVar(value=values.get("titlebar", "true") == "true")
                name_var = tk.StringVar(value=clean_window_title(title, sanitize=True))

                settings_vars[title] = (pos_var, size_var, aot_var, titlebar_var, name_var)
                
                tk.Entry(settings_frame,
                    textvariable=name_var,
                    width=25,
                    bg=self.background,
                    fg=self.text_normal,
                    insertbackground=self.text_normal
                ).grid(row=row, column=0, padx=(0, 10))

                ttk.Label(settings_frame, text="Position (x,y):").grid(row=row, column=1)
                tk.Entry(settings_frame,
                    textvariable=pos_var,
                    width=10,
                    bg=self.background,
                    fg=self.text_normal,
                    insertbackground=self.text_normal
                ).grid(row=row, column=2)

                ttk.Label(settings_frame, text="Size (w,h):").grid(row=row, column=3)
                tk.Entry(settings_frame,
                    textvariable=size_var,
                    width=10,
                    bg=self.background,
                    fg=self.text_normal,
                    insertbackground=self.text_normal
                ).grid(row=row, column=4)

                tk.Checkbutton(settings_frame,
                    text="Always on top",
                    variable=aot_var,
                    bg=self.background,
                    fg=self.text_normal,
                    selectcolor=self.window_normal,
                    activebackground=self.window_normal_dark,
                    activeforeground=self.text_normal
                ).grid(row=row, column=5)
                
                tk.Checkbutton(settings_frame,
                    text="Titlebar",
                    variable=titlebar_var,
                    bg=self.background,
                    fg=self.text_normal,
                    selectcolor=self.window_normal,
                    activebackground=self.window_normal_dark,
                    activeforeground=self.text_normal
                ).grid(row=row, column=6)

            row += 1
            ttk.Label(settings_frame, text="Config Name: ").grid(row=row, column=1, pady=(20, 0), sticky='w')
            config_name_var = tk.StringVar()
            tk.Entry(settings_frame,
                textvariable=config_name_var,
                bg=self.background,
                fg=self.text_normal,
                insertbackground=self.text_normal
                ).grid(row=row, column=2, columnspan=3, pady=(20, 0), sticky='ew')

            self.apply_titlebar_style()

            def on_save():
                config_data = {}
                for title, vars_ in settings_vars.items():
                    pos, size, aot, titlebar, name_var = vars_
                    config_data[title] = {
                        'position': pos.get(),
                        'size': size.get(),
                        'always_on_top': aot.get(),
                        'titlebar': titlebar.get(),
                        'name': name_var.get().strip()
                    }
                name = config_name_var.get().strip()
                name = re.sub(r'[<>:"/\\|?*]', '', name)
                if not name:
                    messagebox.showerror("Error", "Config name is required")
                    return
                if save_callback(name, config_data):
                    if refresh_callback:
                        refresh_callback(name)
                    on_close()

            ttk.Button(settings_frame, text="Save Config", command=on_save).grid(row=row+1, column=0, columnspan=7, pady=15)

        config_win = tk.Toplevel(parent)
        config_win.title("Create Config")
        config_win.configure(bg=self.background)
        
        parent.update_idletasks()
        x = parent.winfo_rootx() + 50
        y = parent.winfo_rooty() + 50
        config_win.geometry(f"+{x}+{y}")
        config_win.update_idletasks()
        config_win.minsize(config_win.winfo_width(), config_win.winfo_height())
        config_win.protocol("WM_DELETE_WINDOW", on_close)
        config_win.transient(parent)
        config_win.lift()
        config_win.focus_set()

        self.apply_titlebar_style()

        select_frame = ttk.Frame(config_win)
        select_frame.configure(style='TFrame')
        select_frame.pack(padx=10, fill='x')

        selection_frame = ttk.Frame(config_win, padding=10)
        selection_frame.configure(style='TFrame')
        selection_frame.pack(fill='both', expand=True)

        ttk.Label(selection_frame, text="Select windows (max 4):").pack(pady=10)

        switches = {}
        for title in window_titles:
            var = tk.BooleanVar()
            cb = tk.Checkbutton(
                selection_frame,
                text=title,
                variable=var,
                bg=self.background,
                fg=self.text_normal,
                selectcolor=self.window_normal,
                activebackground=self.window_normal_dark,
                activeforeground=self.text_normal,
                relief=tk.FLAT,
                highlightthickness=0,
                bd=0
            )

            cb.pack(anchor='w')
            switches[title] = var

        ttk.Button(selection_frame, text="Confirm Selection", command=confirm_selection).pack(pady=10)

class ScreenLayoutFrame(ttk.Frame):
    def __init__(self, parent, screen_width, screen_height, windows: List[WindowInfo], theme):
        super().__init__(parent)
        self.windows = windows
        self.update_colors(theme)

        self.canvas = tk.Canvas(self, bg=choose_color(Colors.BACKGROUND, Themes.APPROVED_DARK_THEMES, theme), highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_resize)

        self.screen_width = screen_width
        self.screen_height = screen_height
        self.taskbar_height = UIConstants.TASKBAR_HEIGHT

        self._compute_bounds(include_placeholders=True)

    def update_colors(self, theme):
        self.background = choose_color(Colors.BACKGROUND, Themes.APPROVED_DARK_THEMES, theme)
        self.text_normal = choose_color(Colors.TEXT_NORMAL, Themes.APPROVED_DARK_THEMES, theme)
        self.window_normal = choose_color(Colors.WINDOW_NORMAL, Themes.APPROVED_DARK_THEMES, theme)
        self.window_normal_dark = choose_color(Colors.WINDOW_NORMAL_DARK, Themes.APPROVED_DARK_THEMES, theme)
        self.window_border = choose_color(Colors.WINDOW_BORDER, Themes.APPROVED_DARK_THEMES, theme)
        self.taskbar = choose_color(Colors.TASKBAR, Themes.APPROVED_DARK_THEMES, theme)
        self.window_always_on_top = choose_color(Colors.WINDOW_ALWAYS_ON_TOP, Themes.APPROVED_DARK_THEMES, theme)
        self.text_error = choose_color(Colors.TEXT_ERROR, Themes.APPROVED_DARK_THEMES, theme)
    
    def redraw(self, theme):
        self.canvas.config(bg=(choose_color(Colors.BACKGROUND, Themes.APPROVED_DARK_THEMES, theme)))
        self.update_colors(theme)
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        self._draw_layout(width, height)
    
    def _compute_bounds(self, include_placeholders=False):
        # If no windows, set default bounds to screen size
        if not self.windows:
            self.min_x, self.min_y = 0, 0
            self.max_x, self.max_y = self.screen_width, self.screen_height
            return

        # Include all windows; placeholders for missing windows if needed
        xs = []
        ys = []
        xs_end = []
        ys_end = []

        for w in self.windows:
            xs.append(w.pos_x)
            ys.append(w.pos_y)
            xs_end.append(w.pos_x + w.width)
            ys_end.append(w.pos_y + w.height)

        self.min_x = min(xs)
        self.min_y = min(ys)
        self.max_x = max(xs_end)
        self.max_y = max(ys_end)

    def _on_resize(self, event):
        self._draw_layout(event.width, event.height)

    def _draw_layout(self, width, height):
        self.canvas.delete("all")

        padding = 5
        drawable_height = height - padding * 2
        drawable_width = width - padding * 2

        # Maintain aspect ratio of screen resolution (width/height)
        screen_ratio = self.screen_width / self.screen_height
        canvas_ratio = drawable_width / drawable_height

        if canvas_ratio > screen_ratio:
            # Canvas too wide, scale width down
            scale = drawable_height / self.screen_height
            scaled_width = scale * self.screen_width
            x_offset = (drawable_width - scaled_width) / 2 + padding
            y_offset = padding
        else:
            # Canvas too tall, scale height down
            scale = drawable_width / self.screen_width
            scaled_height = scale * self.screen_height
            x_offset = padding
            y_offset = (drawable_height - scaled_height) / 2 + padding

        # Draw slim frame around the layout area
        frame_left = x_offset
        frame_top = y_offset
        frame_right = x_offset + scale * self.screen_width
        frame_bottom = y_offset + scale * self.screen_height
        frame_width = 5

        self.canvas.create_rectangle(
            frame_left, frame_top, frame_right, frame_bottom,
            outline=self.window_border, width=frame_width
        )

        # Draw the taskbar at bottom inside frame
        self.canvas.create_rectangle(
            frame_left,
            frame_bottom - self.taskbar_height * scale,
            frame_right,
            frame_bottom,
            fill=self.taskbar,
            outline=""
        )

        for win in self.windows:
            x = x_offset + win.pos_x * scale
            y = y_offset + win.pos_y * scale
            w = win.width * scale
            h = win.height * scale

            # Darker background colors for windows
            if win.exists:
                fill_color = (
                    self.window_always_on_top if win.always_on_top else self.window_normal
                )
                border_color = self.window_border
            else:
                fill_color = self.window_always_on_top if win.always_on_top else self.window_normal
                border_color = self.window_border

            # Draw window rectangle
            self.canvas.create_rectangle(
                x, y, x + w, y + h,
                fill=fill_color,
                outline=border_color,
                width=1 if not win.always_on_top else 2
            )

            # Prepare info text lines
            info_lines = [
                win.name,
                f"Pos: {win.pos_x},{win.pos_y}",
                f"Size: {win.width}x{win.height}",
                f"AOT: {'Yes' if win.always_on_top else 'No'}"
            ]

            # Font sizes and styles
            text_color = self.text_normal

            # Text left-aligned, start near top-left inside window rect with some padding
            padding_x = 5  # fixed pixels, no scaling
            padding_y = 5
            line_height = 16  # fixed pixel height per line

            max_lines = int((h - 2 * padding_y) // line_height)
            lines_to_draw = info_lines[:max_lines]  # clip if not enough space

            for i, line in enumerate(lines_to_draw):
                font_to_use = Fonts.TEXT_BOLD if i == 0 else Fonts.TEXT_NORMAL
                self.canvas.create_text(
                    x + padding_x,
                    y + padding_y + i * line_height,
                    text=line,
                    fill=text_color,
                    font=font_to_use,
                    anchor="nw",
                    justify=tk.LEFT
                )

            # If missing, add "MISSING" near bottom inside window rect, centered horizontally
            if not win.exists:
                margin_bottom = 5 * scale
                self.canvas.create_text(
                    x + w / 2,
                    y + h - margin_bottom - 20,
                    text="MISSING",
                    fill=self.text_error,
                    font=("Segoe UI", 9, "bold"),
                    justify=tk.CENTER
                )
