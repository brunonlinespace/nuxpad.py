import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

class LinuxNotepad:
    def __init__(self, root):
        self.root = root
        self.root.title("Untitled - Notepad")
        self.root.geometry("600x400")
        
        self.file_path = None
        self.is_dark_mode = False
        self.content_saved = True

        # Text Widget
        self.text_area = tk.Text(self.root, wrap="word", undo=True)
        self.text_area.pack(fill="both", expand=True)

        # Track modifications to text
        self.text_area.bind('<<Modified>>', self.on_text_modified)

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
        self.file_menu.add_command(label="Exit", command=self.exit_app)

        # Edit Menu (for Search/Find)
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Find...", command=self.find_text)

        # View Menu (for Theme Toggle)
        self.view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)
        self.view_menu.add_command(label="Toggle Dark/Light Mode", command=self.toggle_theme)

        # Handle window close [X] button click
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        # Apply initial theme (Light)
        self.apply_theme()

    def on_text_modified(self, event=None):
        # Tkinter fires this when text changes; check if it's an actual user edit
        if self.text_area.edit_modified():
            self.content_saved = False
            # Update title to show an asterisk for unsaved changes
            current_title = self.root.title()
            if not current_title.startswith("*"):
                self.root.title("*" + current_title)
        # Reset the modified flag so it keeps tracking future edits
        self.text_area.edit_modified(False)

    def check_save_changes(self):
        if not self.content_saved:
            response = messagebox.askyesnocancel("Notepad", "Do you want to save changes?")
            if response is True:  # Yes
                self.save_file()
                return self.content_saved  # Proceed only if successfully saved
            elif response is False:  # No
                return True
            else:  # Cancel
                return False
        return True

    def new_file(self):
        if self.check_save_changes():
            self.text_area.delete("1.0", tk.END)
            self.file_path = None
            self.root.title("Untitled - Notepad")
            self.content_saved = True

    def open_file(self):
        if self.check_save_changes():
            file_path = filedialog.askopenfilename(defaultextension=".txt",
                                                   filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")])
            if file_path:
                self.file_path = file_path
                self.root.title(f"{file_path} - Notepad")
                self.text_area.delete("1.0", tk.END)
                with open(file_path, "r") as file:
                    self.text_area.insert("1.0", file.read())
                self.content_saved = True

    def save_file(self):
        if self.file_path:
            try:
                with open(self.file_path, "w") as file:
                    file.write(self.text_area.get("1.0", tk.END))
                self.content_saved = True
                self.root.title(f"{self.file_path} - Notepad")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file:\n{e}")
        else:
            self.save_as_file()

    def save_as_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")])
        if file_path:
            self.file_path = file_path
            self.save_file()

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
            bg_color = "#1e1e1e"
            fg_color = "#d4d4d4"
            insert_color = "#ffffff"
        else:
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