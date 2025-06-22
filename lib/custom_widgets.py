import tkinter as tk

# Local imports
from lib.constants import Fonts, Colors, Themes
from lib.utils import choose_color

class CustomDropdown(tk.Frame):
    def __init__(self, parent, values, command=None, width=28, **kwargs):
        super().__init__(parent, **kwargs)
        self.values = values
        self.command = command
        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, width=width, bg="black", fg="white", insertbackground="white")
        self.entry.config(insertontime=0)
        self.entry.pack(fill=tk.X, expand=True)
        self.entry.bind("<Button-1>", self.toggle_dropdown)

        # Disable text input
        def block_typing(event):
            if event.keysym not in ("Up", "Down", "Escape", "Tab", "Shift_L", "Shift_R"):
                return "break"

        self.entry.bind("<Key>", block_typing)
        self.entry.bind("<MouseWheel>", self._scroll_through_values)

        self.dropdown = None
        self.listbox = None

    def _on_mousewheel(self, event):
        self.listbox.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def toggle_dropdown(self, event=None):
        if self.dropdown and self.dropdown.winfo_exists():
            self.close_dropdown()
        else:
            self.open_dropdown()

    def open_dropdown(self):
        self.dropdown = tk.Toplevel(self)
        self.dropdown.wm_overrideredirect(True)
        self.dropdown.configure(bg="black")
        self.dropdown.geometry(self.calc_dropdown_geometry())
        self.dropdown.bind("<FocusOut>", lambda e: self.close_dropdown())

        self.listbox = tk.Listbox(self.dropdown, selectmode=tk.SINGLE, bg="black", fg="white", highlightthickness=0, font=Fonts.TEXT_NORMAL)
        for val in self.values:
            self.listbox.insert(tk.END, val)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(self.dropdown, command=self.listbox.yview, background="gray", troughcolor="black")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        self.listbox.bind("<Escape>", lambda e: self.close_dropdown())

        self.dropdown.focus_set()

    def _scroll_through_values(self, event):
        if not self.values:
            return

        current = self.var.get()
        try:
            index = self.values.index(current)
        except ValueError:
            index = 0

        if event.delta > 0:
            index = (index - 1) % len(self.values)
        else:
            index = (index + 1) % len(self.values)

        self.var.set(self.values[index])
        if self.command:
            self.command(self.values[index])

    def close_dropdown(self):
        if self.dropdown and self.dropdown.winfo_exists():
            self.dropdown.destroy()
            self.dropdown = None

    def on_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            selected = self.listbox.get(selection[0])
            self.var.set(selected)
            if self.command:
                self.command(selected)
        self.close_dropdown()

    def calc_dropdown_geometry(self):
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        width = self.entry.winfo_width()
        height = min(len(self.values), 12) * 20
        return f"{width}x{height}+{x}+{y}"
    
    def set_theme(self, theme):
        bg = choose_color(Colors.BACKGROUND, Themes.APPROVED_DARK_THEMES, theme)
        fg = choose_color(Colors.TEXT_NORMAL, Themes.APPROVED_DARK_THEMES, theme)
        highlight = choose_color(Colors.WINDOW_BORDER, Themes.APPROVED_DARK_THEMES, theme)
        listbox_bg = choose_color(Colors.WINDOW_NORMAL, Themes.APPROVED_DARK_THEMES, theme)
        scrollbar_color = choose_color(Colors.WINDOW_NORMAL_DARK, Themes.APPROVED_DARK_THEMES, theme)

        self.entry.configure(bg=bg, fg=fg, insertbackground=fg, highlightbackground=highlight)

        if self.dropdown and self.dropdown.winfo_exists():
            self.dropdown.configure(bg=bg)
            self.listbox.configure(bg=listbox_bg, fg=fg, font=Fonts.TEXT_NORMAL, highlightthickness=0)
            for i in range(self.listbox.size()):
                self.listbox.itemconfig(i, bg=listbox_bg, fg=fg)

            # Recreate scrollbar to apply updated colors
            scrollbar = tk.Scrollbar(self.dropdown, command=self.listbox.yview, background=scrollbar_color, troughcolor=bg)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.listbox.config(yscrollcommand=scrollbar.set)
