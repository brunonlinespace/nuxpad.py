import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

class LinuxNotepad:
    def __init__(self, root):
        self.root = root
        self.file_path = None
        self.is_dark_mode = False
        self.content_saved = True

        # Window Setup
        self.root.title("Untitled - Notepad")
        self.root.geometry("600x400")

        # Text Widget & Scrollbar Container
        self.text_area = tk.Text(self.root, wrap="word", undo=True)
        self.scrollbar = tk.Scrollbar(self.text_area, command=self.text_area.yview)
        
        self.text_area.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.text_area.pack(fill="both", expand=True)

        # Track text modifications safely
        self.text_area.bind('<<Modified>>', self.on_text_modified)

        # Build UI Menus
        self.create_menus()

        # Window close protocol handler
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        # Apply initial theme
        self.apply_theme()

    def create_menus(self):
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        # File Menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        self.file_menu.add_command(label="Open...", command=self.open_file, accelerator="Ctrl+O")
        self.file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        self.file_menu.add_command(label="Save As...", command=self.save_as_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.exit_app)

        # Edit Menu
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Find...", command=self.find_text, accelerator="Ctrl+F")

        # View Menu
        self.view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)
        self.view_menu.add_command(label="Toggle Dark/Light Mode", command=self.toggle_theme)

    def on_text_modified(self, event=None):
        # Prevent tracking changes during programmatic clears/inserts
        if self.text_area.edit_modified():
            if self.content_saved:
                self.content_saved = False
                self.update_title()
        # Reset the internal modified flag
        self.text_area.edit_modified(False)

    def update_title(self):
        display_name = self.file_path if self.file_path else "Untitled"
        prefix = "*" if not self.content_saved else ""
        self.root.title(f"{prefix}{display_name} - Notepad")

    def check_save_changes(self):
        if not self.content_saved:
            response = messagebox.askyesnocancel("Notepad", "Do you want to save changes?")
            if response is True:  # Yes
                return self.save_file()
            elif response is False:  # No
                return True
            else:  # Cancelled
                return False
        return True

    def new_file(self):
        if self.check_save_changes():
            self.text_area.delete("1.0", tk.END)
            self.file_path = None
            self.content_saved = True
            self.text_area.edit_reset()  # Clear undo stack
            self.update_title()

    def open_file(self):
        if self.check_save_changes():
            file_path = filedialog.askopenfilename(
                defaultextension=".txt",
                filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")]
            )
            if file_path:
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                    
                    self.text_area.delete("1.0", tk.END)
                    self.text_area.insert("1.0", content)
                    self.file_path = file_path
                    self.content_saved = True
                    self.text_area.edit_reset()
                    self.update_title()
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open file:\n{e}")

    def save_file(self):
        if self.file_path:
            try:
                with open(self.file_path, "w", encoding="utf-8") as file:
                    file.write(self.text_area.get("1.0", tk.END))
                self.content_saved = True
                self.update_title()
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file:\n{e}")
                return False
        else:
            return self.save_as_file()

    def save_as_file(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            self.file_path = file_path
            return self.save_file()
        return False

    def exit_app(self):
        if self.check_save_changes():
            self.root.destroy()

    def find_text(self):
        self.text_area.tag_remove("match", "1.0", tk.END)
        query = simpledialog.askstring("Find", "Enter text to find:")
        if query:
            idx = "1.0"
            matches = 0
            while True:
                idx = self.text_area.search(query, idx, nocase=True, stopindex=tk.END)
                if not idx:
                    break
                last_idx = f"{idx}+{len(query)}c"
                self.text_area.tag_add("match", idx, last_idx)
                idx = last_idx
                matches += 1
            
            self.text_area.tag_config("match", background="yellow", foreground="black")
            
            if matches == 0:
                messagebox.showinfo("Find", "No matches found.")

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def apply_theme(self):
        if self.is_dark_mode:
            bg_color, fg_color, insert_color = "#1e1e1e", "#d4d4d4", "#ffffff"
        else:
            bg_color, fg_color, insert_color = "#ffffff", "#000000", "#000000"

        self.text_area.config(
            bg=bg_color,
            fg=fg_color,
            insertbackground=insert_color
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = LinuxNotepad(root)
    root.mainloop()