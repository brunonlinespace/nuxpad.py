import tkinter as tk
from tkinter import filedialog, messagebox

class LinuxNotepad:
    def __init__(self, root):
        self.root = root
        self.root.title("Untitled - Notepad")
        self.root.geometry("600x400")
        
        self.file_path = None
        self.is_dark_mode = False

        # Text Widget
        self.text_area = tk.Text(self.root, wrap="word", undo=True)
        self.text_area.pack(fill="both", expand=True)

        # Scrollbar
        self.scrollbar = tk.Scrollbar(self.text_area)
        self.scrollbar.pack(side="right", fill="y")
        self.text_area.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.text_area.yview)

        # Menu Bar
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        # File Menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New", command=self.new_file)
        self.file_menu.add_command(label="Open...", command=self.open_file)
        self.file_menu.add_command(label="Save", command=self.save_file)
        self.file_menu.add_command(label="Save As...", command=self.save_as_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit)

        # View Menu (for Theme Toggle)
        self.view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)
        self.view_menu.add_command(label="Toggle Dark/Light Mode", command=self.toggle_theme)

        # Apply initial theme (Light)
        self.apply_theme()

    def new_file(self):
        self.text_area.delete("1.0", tk.END)
        self.file_path = None
        self.root.title("Untitled - Notepad")

    def open_file(self):
        file_path = filedialog.askopenfilename(defaultextension=".txt",
                                               filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")])
        if file_path:
            self.file_path = file_path
            self.root.title(f"{file_path} - Notepad")
            self.text_area.delete("1.0", tk.END)
            with open(file_path, "r") as file:
                self.text_area.insert("1.0", file.read())

    def save_file(self):
        if self.file_path:
            try:
                with open(self.file_path, "w") as file:
                    file.write(self.text_area.get("1.0", tk.END))
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file:\n{e}")
        else:
            self.save_as_file()

    def save_as_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")])
        if file_path:
            self.file_path = file_path
            self.root.title(f"{file_path} - Notepad")
            self.save_file()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def apply_theme(self):
        if self.is_dark_mode:
            # Dark Theme Colors
            bg_color = "#1e1e1e"
            fg_color = "#d4d4d4"
            insert_color = "#ffffff"
        else:
            # Light Theme Colors
            bg_color = "#ffffff"
            fg_color = "#000000"
            insert_color = "#000000"

        self.text_area.config(
            bg=bg_color,
            fg=fg_color,
            insertbackground=insert_color
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = LinuxNotepad(root)
    root.mainloop()