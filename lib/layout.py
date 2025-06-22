import os
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox
import pywinstyles
from ctypes import windll
from typing import List

# Local imports
from lib.utils import WindowInfo, clean_window_title, choose_color
from lib.constants import UIConstants, Colors, Messages, WindowStyles, Fonts, Themes
from lib.custom_widgets import CustomDropdown
from lib.asset_manager import AssetManager

class TkGUIManager:
    def __init__(self, root, callbacks=None, compact=False, is_admin=False):
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

        self.res_x = self.root.winfo_screenwidth()
        self.res_y = self.root.winfo_screenheight()
        self.pos_x = (self.res_x // 2) - (UIConstants.WINDOW_WIDTH // 2)
        self.pos_y = (self.res_y // 2) - (UIConstants.WINDOW_HEIGHT // 2)
        self.root.geometry(f"{UIConstants.WINDOW_WIDTH}x{UIConstants.WINDOW_HEIGHT}+{self.pos_x}+{self.pos_y}")

        self.compact_mode = compact or False
        self.is_admin = is_admin

        self.default_font = Fonts.TEXT_NORMAL
        self.canvas = None
        self.buttons_container = None
        self.managed_label = None
        self.managed_text = None

        self.callbacks = callbacks or {}

        self.apply_config = None
        self.reset_config = None
        self.create_config = None
        self.delete_config = None
        self.open_config_folder = None
        self.restart_as_admin = None
        self.toggle_AOT = None
        self.toggle_images = None

        self.on_config_select = None
        self.on_mode_toggle = None
        
        self.layout_frame_create_config = None
        self.image_cache = {}
        self.asset_manager = AssetManager()
        self.use_images = False
        self.failed_downloads = []

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
        self.text_dim = choose_color(Colors.TEXT_DIM, Themes.APPROVED_DARK_THEMES, self.theme)

        style.configure("TFrame", background=self.background)
        
        style.configure("TLabel",
            font=self.default_font,
            background=self.background,
            foreground=self.text_normal
        )

        style.configure("Admin.TLabel",
            font=Fonts.TEXT_BOLD,
            background=self.background,
            foreground=Colors.ADMIN_ENABLED
        )
        
        style.configure("TButton",
            font=self.default_font,
            background=self.background,
            foreground=self.text_normal,
            activebackground=self.window_normal,
            activeforeground=self.text_normal
        )
        style.map("TButton", background=[('active', self.window_normal)], foreground=[('active', self.text_normal)])

        style.configure("Disabled.TButton",
            font=Fonts.TEXT_NORMAL,
            foreground=self.text_dim,
            background=self.window_normal_dark,
            borderwidth=0
        )
        
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
        self.resolution_label = ttk.Label(header_frame, text=f"Screen: {self.res_x} x {self.res_y}", padding=(0, 0, 5, 0))
        self.resolution_label.configure(style='TLabel')
        self.resolution_label.pack(side=tk.LEFT, fill=tk.X)

        # User / Admin mode label
        app_mode = "Admin" if self.is_admin else "User"
        self.admin_label = ttk.Label(header_frame, text=f"Mode: {app_mode}", padding=(0, 0, 5, 0))
        self.admin_label.configure(style='Admin.TLabel' if self.is_admin else 'TLabel')
        self.admin_label.pack(side=tk.RIGHT, fill=tk.X)
        
        combo_frame = header_frame = ttk.Frame(self.main_frame, padding=UIConstants.MARGIN)
        combo_frame.configure(style="TFrame")
        combo_frame.pack(side=tk.TOP, fill=tk.X)
        self.combo_box = CustomDropdown(combo_frame, values=[], command=self.callbacks.get("config_selected", self.on_config_select))
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
        buttons_1 = [
            ("Apply config", self.callbacks.get("apply_config") or self.apply_config),
            ("Reset config", self.callbacks.get("reset_config") or self.reset_config),
            ("Create config", self.callbacks.get("create_config") or self.create_config),
            ("Delete Config", self.callbacks.get("delete_config") or self.delete_config),
        ]
        
        buttons_2 = [
            ("Open config folder", self.callbacks.get("open_config_folder") or self.open_config_folder),
            ("Restart as Admin", self.callbacks.get("restart_as_admin") or self.restart_as_admin),
            ("Toggle compact", self.callbacks.get("toggle_compact") or self.toggle_compact),
            ("Change theme", self.callbacks.get("theme") or self.change_gui_theme)
        ]

        self.buttons_1_container = ttk.Frame(main_buttons)
        self.buttons_1_container.pack(side=tk.TOP, fill=tk.X, expand=True, anchor=tk.CENTER)
        
        total_buttons_1_width = len(buttons_1) * 100
        self.buttons_1_container.configure(width=total_buttons_1_width)
        for name, command in buttons_1:
            btn = ttk.Button(self.buttons_1_container, text=name, command=command, width=20)
            btn.pack(side=tk.LEFT, padx=UIConstants.MARGIN[2], pady=UIConstants.MARGIN[0], fill=tk.X, expand=True)

        self.buttons_2_container = ttk.Frame(main_buttons)
        self.buttons_2_container.pack(side=tk.TOP, fill=tk.X, expand=True, anchor=tk.CENTER)
        
        total_buttons_2_width = len(buttons_2) * 100
        self.buttons_2_container.configure(width=total_buttons_2_width)
        for name, command in buttons_2:
            adm = (self.is_admin and name == "Restart as Admin")
            btn = ttk.Button(self.buttons_2_container,
                text=name,
                command=command,
                width=20,
                state=tk.DISABLED if adm else tk.NORMAL,
                style='Disabled.TButton' if adm else 'TButton',
            )
            btn.pack(side=tk.LEFT, padx=UIConstants.MARGIN[2], pady=UIConstants.MARGIN[0], fill=tk.X, expand=True)

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
        self.aot_button_frame = ttk.Frame(aot_container, padding=UIConstants.MARGIN)
        self.aot_button_frame.configure(style="TFrame")
        self.aot_button_frame.pack(side=tk.TOP, fill=tk.X, pady=(UIConstants.MARGIN[2], 0))
        aot_button = ttk.Button(self.aot_button_frame, text="Toggle AOT", width=20,
                                command=self.callbacks.get("toggle_AOT") or self.toggle_AOT)
        aot_button.pack(side=tk.LEFT, anchor=tk.W)

        # Image toggle button
        self.image_button = ttk.Button(self.aot_button_frame, text="Toggle images", width=20,
                                command=self.callbacks.get("toggle_images") or self.toggle_images)
        self.image_button.pack(side=tk.RIGHT, anchor=tk.W)

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

    def remove_managed_windows_frame(self):
        if self.managed_label:
            self.managed_label.destroy()
            self.managed_label = None
        if self.managed_text:
            self.managed_text.destroy()
            self.managed_text = None
        self.managed_frame.pack_forget()
    
    def set_layout_frame(self, windows):
        # Clear old frame
        if self.layout_frame:
            self.layout_frame.destroy()

        # Create and pack new layout frame
        self.layout_frame = ScreenLayoutFrame(self.layout_container, self.res_x, self.res_y, windows, self.theme, self.image_cache, asset_manager=self.asset_manager, use_images=self.use_images, failed_downloads=self.failed_downloads)
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

            # Redrawing canvas
            canvas = self.layout_frame
            canvas.redraw(self.theme)

            # Applying new style
            self.setup_styles()
            self.combo_box.set_theme(self.theme)
            self.root.after(100, self.apply_titlebar_style)
            if self.compact_mode:
                self.remove_managed_windows_frame()
                self.setup_managed_text()
            
            self.scale_gui()
        except Exception as e:
            print("Theme change failed:", e)

    def toggle_compact(self, startup=False):
        if not startup: self.compact_mode = not self.compact_mode
        if self.compact_mode:
            if self.layout_container:
                self.layout_container.pack_forget()

            for child in self.buttons_1_container.winfo_children():
                child.pack_configure(side=tk.TOP, fill=tk.X)
            
            for child in self.buttons_2_container.winfo_children():
                child.pack_configure(side=tk.TOP, fill=tk.X)
            
            self.image_button.destroy()

            self.setup_managed_text()
        else:
            if self.layout_container:
                self.layout_container.pack(before=self.button_frame, side=tk.TOP, fill=tk.BOTH, expand=True)

            for child in self.buttons_1_container.winfo_children():
                if isinstance(child, ttk.Button):
                    child.pack_configure(side=tk.LEFT, fill=tk.X)
            
            for child in self.buttons_2_container.winfo_children():
                if isinstance(child, ttk.Button):
                    child.pack_configure(side=tk.LEFT, fill=tk.X)

            self.remove_managed_windows_frame()

            self.image_button = ttk.Button(self.aot_button_frame, text="Toggle images", width=20,
                                command=self.callbacks.get("toggle_images") or self.toggle_images)
            self.image_button.pack(side=tk.RIGHT, anchor=tk.W)
        
        self.scale_gui()

    def create_config_ui(self, parent, window_titles, save_callback, settings_callback, refresh_callback):
        parent.attributes('-disabled', True)
        entry_font = ('Consolas 12')

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

            sorted_windows = sorted(
                selected_windows,
                key=lambda title: int((settings_callback(title) or {}).get("position", "0,0").split(",")[0])
            )

            settings_vars = {}
            for row, title in enumerate(sorted_windows):
                values = settings_callback(title) or {}
                pos_var = tk.StringVar(value=values.get("position", "0,0"))
                size_var = tk.StringVar(value=values.get("size", "100,100"))
                aot_var = tk.BooleanVar(value=values.get("always_on_top", "false") == "true")
                titlebar_var = tk.BooleanVar(value=values.get("titlebar", "true") == "true")
                name_var = tk.StringVar(value=clean_window_title(title, sanitize=True))

                settings_vars[title] = [pos_var, size_var, aot_var, titlebar_var, name_var]

                tk.Entry(settings_frame,
                    textvariable=name_var,
                    width=25,
                    bg=self.background,
                    fg=self.text_normal,
                    insertbackground=self.text_normal,
                    font=entry_font
                ).grid(row=row, column=0, padx=(0, 10))

                ttk.Label(settings_frame, text="Position (x,y):", font=entry_font).grid(row=row, column=1)
                tk.Entry(settings_frame,
                    textvariable=pos_var,
                    width=10,
                    bg=self.background,
                    fg=self.text_normal,
                    insertbackground=self.text_normal,
                    font=entry_font
                ).grid(row=row, column=2)

                ttk.Label(settings_frame, text="Size (w,h):", font=entry_font).grid(row=row, column=3)
                tk.Entry(settings_frame,
                    textvariable=size_var,
                    width=10,
                    bg=self.background,
                    fg=self.text_normal,
                    insertbackground=self.text_normal,
                    font=entry_font
                ).grid(row=row, column=4)

                tk.Checkbutton(settings_frame,
                    text="Always on top",
                    variable=aot_var,
                    bg=self.background,
                    fg=self.text_normal,
                    selectcolor=self.window_normal,
                    activebackground=self.window_normal_dark,
                    activeforeground=self.text_normal,
                    font=entry_font
                ).grid(row=row, column=5)
                
                tk.Checkbutton(settings_frame,
                    text="Titlebar",
                    variable=titlebar_var,
                    bg=self.background,
                    fg=self.text_normal,
                    selectcolor=self.window_normal,
                    activebackground=self.window_normal_dark,
                    activeforeground=self.text_normal,
                    font=entry_font
                ).grid(row=row, column=6)

            row += 1
            pady = (20,0)
            ttk.Label(settings_frame, text="Config Name: ", font=entry_font).grid(row=row, column=1, pady=pady)
            config_name_var = tk.StringVar()
            tk.Entry(settings_frame,
                textvariable=config_name_var,
                bg=self.background,
                fg=self.text_normal,
                insertbackground=self.text_normal
                ).grid(row=row, column=2, columnspan=2, pady=pady, sticky='ew')

            self.apply_titlebar_style()

            # Layout frame placeholder
            layout_container_create_config = ttk.Frame(settings_frame, padding=UIConstants.MARGIN)
            layout_container_create_config.configure(style="TFrame")
            layout_container_create_config.grid(row=row+2, column=0, columnspan=7, sticky='nsew')
            settings_frame.rowconfigure(row+2, weight=10)
            for col in range(7):
                settings_frame.columnconfigure(col, weight=1)
            self.layout_frame_create_config = None  # Will hold the ScreenLayoutFrame for create config

            def validate_int_pair(value, default=(0,0)):
                try:
                    x, y = map(int, value.split(','))
                    return x, y
                except (ValueError, AttributeError):
                    return default

            def update_layout_frame():
                windows = []
                try:
                    for title, vars_ in settings_vars.items():
                        pos, size, aot, titlebar, name_var = vars_
                        name = name_var.get().strip() or ''
                        pos_x, pos_y = validate_int_pair(pos.get())
                        size_w, size_h = validate_int_pair(size.get())
                        always_on_top = aot.get() or False
                        window_exists = True
                        windows.append(WindowInfo(name,
                                                pos_x, pos_y,
                                                size_w, size_h,
                                                always_on_top,
                                                window_exists,
                                                search_title=''
                                                ))
                    # Remove the old layout before redrawing
                    if self.layout_frame_create_config:
                        self.layout_frame_create_config.destroy()                    

                    self.layout_frame_create_config = ScreenLayoutFrame(layout_container_create_config,
                                                                self.root.winfo_screenwidth(),
                                                                self.root.winfo_screenheight(),
                                                                windows,
                                                                self.theme,
                                                                self.image_cache,
                                                                self.asset_manager,
                                                                self.failed_downloads
                                                                )
                    self.layout_frame_create_config.pack(expand=True, fill='both')
                except Exception as e:
                    print(f"Failed to draw layout: {e}")

            def auto_position():
                for num, title in enumerate(sorted_windows):
                    vars = settings_vars[title]
                    size_w = self.root.winfo_screenwidth() / len(sorted_windows)
                    size_h = self.root.winfo_screenheight() if vars[2].get() else self.root.winfo_screenheight() - UIConstants.TASKBAR_HEIGHT
                    pos_x = size_w * num
                    settings_vars[title][0].set(f'{int(pos_x)},0')
                    settings_vars[title][1].set(f'{int(size_w)},{int(size_h)}')
                update_layout_frame()

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
                name = clean_window_title(config_name_var.get())
                if not name:
                    messagebox.showerror("Error", "Config name is required")
                    return
                if save_callback(name, config_data):
                    if refresh_callback:
                        refresh_callback(name)
                    on_close()

            update_layout_frame()
            ttk.Button(settings_frame, text="Auto align", command=auto_position, width=15).grid(row=row, column=0, pady=pady, sticky='w')
            ttk.Button(settings_frame, text="Update drawing", command=update_layout_frame, width=15).grid(row=row+1, column=0, pady=pady, sticky='w')
            ttk.Button(settings_frame, text="Save Config", command=on_save, width=30).grid(row=row, column=4, columnspan=2, pady=pady)

            config_win.geometry(f"{UIConstants.WINDOW_WIDTH+200}x{UIConstants.WINDOW_HEIGHT+100}")

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

        ttk.Label(selection_frame, text="Select windows (max 4):", font=entry_font).pack(pady=10)

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
                bd=0,
                font=entry_font
            )

            cb.pack(anchor='w')
            switches[title] = var

        ttk.Button(selection_frame, text="Confirm Selection", command=confirm_selection, width=45).pack(pady=10)



#################################
#                               #
#   Screen layout canvas class  #
#                               #
#################################


class ScreenLayoutFrame(ttk.Frame):
    def __init__(self, parent, screen_width, screen_height, windows: List[WindowInfo], theme, image_cache, asset_manager, failed_downloads, use_images=False):
        super().__init__(parent)
        self.windows = windows
        self.update_colors(theme)
        
        self.asset_manager = asset_manager
        self.assets_dir = "assets"
        self.image_cache = image_cache
        self.use_images = use_images
        self.failed_downloads = failed_downloads

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

        # Draw frame around the layout area
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

            border_color = self.window_border
            fill_color = self.window_always_on_top if win.always_on_top else self.window_normal
                
            # Draw window rectangle
            self.canvas.create_rectangle(
                x, y, x + w, y + h,
                fill=fill_color,
                outline=border_color,
                width=2 if not win.always_on_top else 3
                )

            if self.use_images:
                # Load image if it exists
                image_paths = [
                    os.path.join(self.assets_dir, f"{win.search_title.replace(' ', '_').replace(':', '')}.jpg"),
                    os.path.join(self.assets_dir, f"{win.search_title.replace(' ', '_').replace(':', '')}.png")
                ]
                for image_path in image_paths:
                    if os.path.exists(image_path):
                        try:
                            image = Image.open(image_path)
                            image = image.resize((int(w), int(h)), Image.LANCZOS)
                            tk_image = ImageTk.PhotoImage(image)
                            self.image_cache[image_path] = (image, tk_image)
                            self.canvas.create_image(x, y, image=tk_image, anchor=tk.NW)
                            break
                        except Exception as e:
                            print(f"Error loading image: {e}")
                    elif image_path in self.failed_downloads:
                        #print("Download failed, creating dummy image")
                        shade = 100
                        image = Image.new('RGB', (1,1), (shade,shade,shade))
                        image.save(image_path)
                        break
                    else:
                        print(f"Attempting to download image for {win.search_title}")
                        # Download image
                        download_success = self.asset_manager.search(win.search_title, save_dir=self.assets_dir)
                        if download_success:
                            #print(f"Image downloaded to {image_path}")
                            self._draw_layout(width, height)
                        else:
                            self.failed_downloads.append(image_path)
                        break

            # Prepare info text lines
            info_lines = [
                win.search_title or win.name,
                f"Pos: {win.pos_x},{win.pos_y}",
                f"Size: {win.width}x{win.height}",
                f"AOT: {'Yes' if win.always_on_top else 'No'}"
            ]

            # Font sizes and styles
            text_color = self.text_normal
            padding_x = 5
            padding_y = 5
            line_height = 16

            max_lines = int((h - 2 * padding_y) // line_height)
            lines_to_draw = info_lines[:max_lines]

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

            # Add missing text
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
