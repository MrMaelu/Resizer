import tkinter as tk
import json
import pygetwindow as gw
import win32gui
import win32con

class WindowPositioner:
    def __init__(self, master):
        self.master = master
        master.title("Window Positioner")

        self.config_file = "config.json"
        self.layouts = self.load_config()

        self.layout_list = tk.Listbox(master)
        for layout in self.layouts:
            self.layout_list.insert(tk.END, layout["name"])
        self.layout_list.pack()

        # Entry fields for layout properties
        self.name_label = tk.Label(master, text="Name:")
        self.name_label.pack()
        self.name_entry = tk.Entry(master)
        self.name_entry.pack()

        self.title_label = tk.Label(master, text="Title:")
        self.title_label.pack()
        self.title_entry = tk.Entry(master)
        self.title_entry.pack()

        self.position_label = tk.Label(master, text="Position (x, y):")
        self.position_label.pack()
        self.position_entry = tk.Entry(master)
        self.position_entry.pack()

        self.size_label = tk.Label(master, text="Size (width, height):")
        self.size_label.pack()
        self.size_entry = tk.Entry(master)
        self.size_entry.pack()

        # Checkbuttons for always_on_top and titlebar
        self.always_on_top_var = tk.BooleanVar()
        self.always_on_top_check = tk.Checkbutton(master, text="Always On Top", variable=self.always_on_top_var)
        self.always_on_top_check.pack()

        self.titlebar_var = tk.BooleanVar()
        self.titlebar_check = tk.Checkbutton(master, text="Titlebar", variable=self.titlebar_var)
        self.titlebar_check.pack()

        # Canvas for visual representation
        self.canvas = tk.Canvas(master, width=200, height=100, bg="white")
        self.canvas.pack()

        self.add_button = tk.Button(master, text="Add", command=self.add_layout)
        self.add_button.pack()

        self.edit_button = tk.Button(master, text="Edit", command=self.edit_layout)
        self.edit_button.pack()

        self.delete_button = tk.Button(master, text="Delete", command=self.delete_layout)
        self.delete_button.pack()

        self.apply_button = tk.Button(master, text="Apply", command=self.apply_layout)
        self.apply_button.pack()

        # Bind select event to listbox
        self.layout_list.bind('<<ListboxSelect>>', self.on_select)

        # Initial draw
        self.screen_width = 1920  # Replace with your screen width
        self.screen_height = 1080 # Replace with your screen height
        self.draw_screen_layout()

    def on_select(self, event):
        selected_index = self.layout_list.curselection()
        if selected_index:
            selected_index = selected_index[0]
            layout = self.layouts[selected_index]
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, layout["name"])
            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, layout["title"])
            self.position_entry.delete(0, tk.END)
            self.position_entry.insert(0, f"{layout['position'][0]}, {layout['position'][1]}")
            self.size_entry.delete(0, tk.END)
            self.size_entry.insert(0, f"{layout['size'][0]}, {layout['size'][1]}")
            self.always_on_top_var.set(layout["always_on_top"])
            self.titlebar_var.set(layout["titlebar"])
        self.draw_screen_layout()

    def draw_screen_layout(self):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        # Draw screen border
        self.canvas.create_rectangle(5, 5, width - 5, height - 5, outline="black")

        selected_index = self.layout_list.curselection()
        if selected_index:
            selected_index = selected_index[0]
            layout = self.layouts[selected_index]
            
            # Scale window position and size to canvas
            x = layout["position"][0] * (width / self.screen_width)
            y = layout["position"][1] * (height / self.screen_height)
            w = layout["size"][0] * (width / self.screen_width)
            h = layout["size"][1] * (height / self.screen_height)

            # Draw window rectangle
            self.canvas.create_rectangle(x, y, x + w, y + h, fill="lightblue", outline="blue")

    def set_always_on_top(self, hwnd, enable):
        try:
            flag = win32con.HWND_TOPMOST if enable else win32con.HWND_NOTOPMOST
            win32gui.SetWindowPos(hwnd, flag, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOOWNERZORDER)
        except Exception as e:
            print(f"Error setting always on top for hwnd: {hwnd}, enable: {enable}, error: {e}")

    def remove_titlebar(self, hwnd):
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        try:
            style &= ~win32con.WS_CAPTION
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_FRAMECHANGED)
        except Exception as e:
            print(f"Error removing titlebar for hwnd: {hwnd}, error: {e}")

    def restore_titlebar(self, hwnd):
        try:
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            # Check if WS_CAPTION is already present to avoid adding it multiple times
            if not (style & win32con.WS_CAPTION):
                style |= win32con.WS_CAPTION
                win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
                # Force redraw to show the title bar
                win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_FRAMECHANGED | win32con.SWP_SHOWWINDOW)
        except Exception as e:
            print(f"Error restoring titlebar for hwnd: {hwnd}, error: {e}")

root = tk.Tk()
wp = WindowPositioner(root)
root.mainloop()
