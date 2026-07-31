import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, font

class LinuxWordPad:
    def __init__(self, root):
        self.root = root
        self.file_path = None
        self.is_dark_mode = False
        self.content_saved = True

        # Window Setup
        self.root.title("Untitled - WordPad")
        self.root.geometry("700x500")

        # Base Font Configuration
        self.base_font_family = "Arial"
        self.base_font_size = 11
        self.normal_font = font.Font(family=self.base_font_family, size=self.base_font_size)

        # Text Widget & Scrollbar Container
        self.text_area = tk.Text(self.root, wrap="word", undo=True, font=self.normal_font, relief="flat", bd=5)
        self.scrollbar = tk.Scrollbar(self.text_area, command=self.text_area.yview)
        
        self.text_area.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.text_area.pack(fill="both", expand=True)

        # Configure basic formatting tags safely
        self.setup_tags()

        # Track text modifications safely
        self.text_area.bind('<<Modified>>', self.on_text_modified)

        # Bind Core Shortcuts Only (File/Find)
        self.bind_shortcuts()

        # Build UI Menus
        self.create_menus()

        # Window close protocol handler
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        # Apply initial theme (Light)
        self.apply_theme()

    def setup_tags(self):
        bold_font = font.Font(family=self.base_font_family, size=self.base_font_size, weight="bold")
        italic_font = font.Font(family=self.base_font_family, size=self.base_font_size, slant="italic")
        underline_font = font.Font(family=self.base_font_family, size=self.base_font_size, underline=True)

        self.text_area.tag_configure("bold", font=bold_font)
        self.text_area.tag_configure("italic", font=italic_font)
        self.text_area.tag_configure("underline", font=underline_font)

    def bind_shortcuts(self):
        self.root.bind("<Control-n>", lambda event: self.new_file())
        self.root.bind("<Control-o>", lambda event: self.open_file())
        self.root.bind("<Control-s>", lambda event: self.save_file())
        self.root.bind("<Control-f>", lambda event: self.find_text())

    def create_menus(self):
        self.menu_bar = tk.Menu(self.root, tearoff=0)
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
        self.edit_menu.add_command(label="Undo", command=self.text_edit_undo, accelerator="Ctrl+Z")
        self.edit_menu.add_command(label="Redo", command=self.text_edit_redo, accelerator="Ctrl+Y")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Find...", command=self.find_text, accelerator="Ctrl+F")

        # Format Menu
        self.format_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Format", menu=self.format_menu)
        self.format_menu.add_command(label="Bold", command=lambda: self.toggle_tag("bold"))
        self.format_menu.add_command(label="Italic", command=lambda: self.toggle_tag("italic"))
        self.format_menu.add_command(label="Underline", command=lambda: self.toggle_tag("underline"))
        self.format_menu.add_separator()
        self.format_menu.add_command(label="Insert Bullet List", command=self.insert_bullet_point)

        # View Menu
        self.view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)
        self.view_menu.add_command(label="Toggle Dark/Light Mode", command=self.toggle_theme)

    def text_edit_undo(self):
        try:
            self.text_area.edit_undo()
        except tk.TclError:
            pass

    def text_edit_redo(self):
        try:
            self.text_area.edit_redo()
        except tk.TclError:
            pass

    def toggle_tag(self, tag_name):
        try:
            if self.text_area.tag_ranges("sel"):
                current_tags = self.text_area.tag_names("sel.first")
                if tag_name in current_tags:
                    self.text_area.tag_remove(tag_name, "sel.first", "sel.last")
                else:
                    self.text_area.tag_add(tag_name, "sel.first", "sel.last")
        except tk.TclError:
            pass

    def insert_bullet_point(self):
        self.text_area.insert(tk.INSERT, "\n• ")

    def on_text_modified(self, event=None):
        if self.text_area.edit_modified():
            if self.content_saved:
                self.content_saved = False
                self.update_title()
        self.text_area.edit_modified(False)

    def update_title(self):
        display_name = self.file_path if self.file_path else "Untitled"
        prefix = "*" if not self.content_saved else ""
        self.root.title(f"{prefix}{display_name} - WordPad")

    def check_save_changes(self):
        if not self.content_saved:
            response = messagebox.askyesnocancel("WordPad", "Do you want to save changes?")
            if response is True:
                return self.save_file()
            elif response is False:
                return True
            else:
                return False
        return True

    def new_file(self):
        if self.check_save_changes():
            self.text_area.delete("1.0", tk.END)
            self.file_path = None
            self.content_saved = True
            self.text_area.edit_reset()
            self.update_title()
        return "break"

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
        return "break"

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
        return "break"

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def apply_theme(self):
        if self.is_dark_mode:
            bg_color = "#1e1e1e"
            fg_color = "#d4d4d4"
            insert_color = "#ffffff"
            menu_bg = "#2d2d2d"
            menu_fg = "#d4d4d4"
            menu_active_bg = "#3f3f46"
        else:
            bg_color = "#ffffff"
            fg_color = "#000000"
            insert_color = "#000000"
            menu_bg = "#f0f0f0"
            menu_fg = "#000000"
            menu_active_bg = "#e5e5e5"

        # Configure main window background
        self.root.config(bg=bg_color)

        # Configure text box colors
        self.text_area.config(
            bg=bg_color,
            fg=fg_color,
            insertbackground=insert_color,
            selectbackground="#264f78" if self.is_dark_color_needed() or self.is_dark_mode else "#accced"
        )

        # Apply custom theme options to the menus where supported
        for menu in (self.file_menu, self.edit_menu, self.format_menu, self.view_menu, self.menu_bar):
            menu.config(bg=menu_bg, fg=menu_fg, activebackground=menu_active_bg, activeforeground=menu_fg)

    def is_dark_color_needed(self):
        return self.is_dark_mode

if __name__ == "__main__":
    root = tk.Tk()
    app = LinuxWordPad(root)
    root.mainloop()