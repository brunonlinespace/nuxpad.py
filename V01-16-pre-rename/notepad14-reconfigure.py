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
        self.root.geometry("750x550")

        # Base Font Configuration
        self.base_font_family = "Arial"
        self.base_font_size = 11
        self.normal_font = font.Font(family=self.base_font_family, size=self.base_font_size)

        # Toolbar Frame (Container for buttons) - Placed at the BOTTOM, bezel-less (relief="flat", bd=0)
        self.toolbar = tk.Frame(self.root, bd=0, relief="flat")
        self.toolbar.pack(side="bottom", fill="x", padx=5, pady=5)

        # Text Widget & Scrollbar Container - Placed at the TOP, expanding to fill space
        self.text_area = tk.Text(self.root, wrap="word", undo=True, font=self.normal_font, relief="flat", bd=5)
        self.scrollbar = tk.Scrollbar(self.text_area, command=self.text_area.yview)
        
        self.text_area.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.text_area.pack(fill="both", expand=True)

        # Configure formatting tags
        self.setup_tags()

        # Track text modifications safely
        self.text_area.bind('<<Modified>>', self.on_text_modified)

        # Bind Core Shortcuts
        self.bind_shortcuts()

        # Build Toolbar Buttons (centered via an inner subframe)
        self.create_toolbar_buttons()

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

    def create_toolbar_buttons(self):
        self.buttons = []

        # Inner frame packed inside the bottom toolbar to easily center all buttons together (flat, bezel-less)
        self.button_inner_frame = tk.Frame(self.toolbar, bd=0, relief="flat")
        self.button_inner_frame.pack(anchor="center", pady=2)

        def add_btn(text, command, padx=5):
            # Flat, bezel-less button style so they blend nicely with the background
            btn = tk.Button(self.button_inner_frame, text=text, command=command, relief="flat", bd=0, padx=padx, cursor="hand2")
            btn.pack(side="left", padx=3, pady=2)
            self.buttons.append(btn)
            return btn

        # File Operations
        add_btn("New", self.new_file)
        add_btn("Open", self.open_file)
        add_btn("Save", self.save_file)
        add_btn("Save As", self.save_as_file)

        # Edit Operations
        add_btn("Undo", self.text_edit_undo)
        add_btn("Redo", self.text_edit_redo)
        add_btn("Find", self.find_text)

        # Formatting Operations
        add_btn("B", lambda: self.toggle_tag("bold"))
        add_btn("I", lambda: self.toggle_tag("italic"))
        add_btn("U", lambda: self.toggle_tag("underline"))
        add_btn("• List", self.insert_bullet_point)

        # Theme Toggle Button (Icon only)
        self.theme_btn = add_btn("🌙", self.toggle_theme, padx=8)

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
        current_index = self.text_area.index(tk.INSERT)
        line_start = self.text_area.index(f"{current_index} linestart")
        line_end = self.text_area.index(f"{current_index} lineend")
        line_content = self.text_area.get(line_start, line_end)

        if line_content.strip() == "":
            self.text_area.insert(current_index, "• ")
        else:
            self.text_area.insert(current_index, "\n• ")

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
            toolbar_bg = "#1e1e1e"          # Blends seamlessly with the text area
            btn_bg = "#2d2d2d"              # Subtle distinction for buttons
            btn_fg = "#d4d4d4"
            btn_active_bg = "#3f3f46"
            select_bg = "#264f78"
            self.theme_btn.config(text="☀️")
        else:
            bg_color = "#ffffff"
            fg_color = "#000000"
            insert_color = "#000000"
            toolbar_bg = "#ffffff"          # Blends seamlessly with the text area
            btn_bg = "#f0f0f0"              # Subtle distinction for buttons
            btn_fg = "#000000"
            btn_active_bg = "#e0e0e0"
            select_bg = "#accced"
            self.theme_btn.config(text="🌙")

        # Configure window, toolbar containers, and inner frame background to match seamlessly
        self.root.config(bg=bg_color)
        self.toolbar.config(bg=toolbar_bg)
        self.button_inner_frame.config(bg=toolbar_bg)

        # Configure text box colors
        self.text_area.config(
            bg=bg_color,
            fg=fg_color,
            insertbackground=insert_color,
            selectbackground=select_bg
        )

        # Update all toolbar buttons dynamically with flat styling
        for btn in self.buttons:
            btn.config(bg=btn_bg, fg=btn_fg, activebackground=btn_active_bg, activeforeground=fg_color)

if __name__ == "__main__":
    root = tk.Tk()
    app = LinuxWordPad(root)
    root.mainloop()