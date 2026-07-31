#!/usr/bin/env python3
# ==============================================================================
# Nuxpad
# Copyright (C) 2026 AI Collaborator / brunonlinespace
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.licenses.org/licenses/gpl-3.0.html>.
#
# nuxpad.py
# Version: 17 (Program Rename)
# ==============================================================================

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, font

class Nuxpad:
    def __init__(self, root):
        self.root = root
        self.file_path = None
        self.content_saved = True
        
        self.config_file = os.path.expanduser("~/.nuxpad_config.json")
        self.is_dark_mode = self.load_theme_preference()

        # Window Setup
        self.root.title("Untitled - Nuxpad")
        self.root.geometry("800x550")

        # Base Font Configuration
        self.base_font_family = "Arial"
        self.base_font_size = 11
        self.normal_font = font.Font(family=self.base_font_family, size=self.base_font_size)

        # Toolbar Frame (Container for buttons) - Placed at the BOTTOM, bezel-less
        self.toolbar = tk.Frame(self.root, bd=0, relief="flat")
        self.toolbar.pack(side="bottom", fill="x", padx=5, pady=5)

        # Main Editor Container Frame
        self.editor_frame = tk.Frame(self.root, bd=0, relief="flat")
        self.editor_frame.pack(side="top", fill="both", expand=True)

        # Line Numbers Canvas
        self.line_numbers = tk.Canvas(self.editor_frame, width=45, bd=0, highlightthickness=0)
        self.line_numbers.pack(side="left", fill="y")

        # Text Widget & Scrollbar Container
        self.text_area = tk.Text(self.editor_frame, wrap="word", undo=True, font=self.normal_font, relief="flat", bd=5)
        self.scrollbar = tk.Scrollbar(self.editor_frame, command=self.text_area.yview)
        
        self.text_area.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.text_area.pack(side="right", fill="both", expand=True)

        # Configure formatting tags
        self.setup_tags()

        # Track text modifications and updates for line numbers
        self.text_area.bind('<<Modified>>', self.on_text_modified)
        self.text_area.bind('<KeyRelease>', self.update_line_numbers)
        self.text_area.bind('<MouseWheel>', self.update_line_numbers)
        self.text_area.bind('<Button-1>', self.update_line_numbers)

        # Bind Core Shortcuts
        self.bind_shortcuts()

        # Build Toolbar Buttons (Left aligned group + Right aligned theme button)
        self.create_toolbar_buttons()

        # Window close protocol handler
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        # Apply initial theme based on loaded preferences
        self.apply_theme()
        self.update_line_numbers()

    def load_theme_preference(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("dark_mode", False)
        except Exception:
            pass
        return False

    def save_theme_preference(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({"dark_mode": self.is_dark_mode}, f)
        except Exception:
            pass

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

        # Left Frame for standard action buttons
        self.left_toolbar = tk.Frame(self.toolbar, bd=0, relief="flat")
        self.left_toolbar.pack(side="left", anchor="w")

        # Right Frame exclusively for the theme toggle button
        self.right_toolbar = tk.Frame(self.toolbar, bd=0, relief="flat")
        self.right_toolbar.pack(side="right", anchor="e")

        def add_btn(parent, text, command, padx=5):
            btn = tk.Button(parent, text=text, command=command, relief="flat", bd=0, padx=padx, cursor="hand2")
            btn.pack(side="left", padx=3, pady=2)
            self.buttons.append(btn)
            return btn

        # File Operations
        add_btn(self.left_toolbar, "New", self.new_file)
        add_btn(self.left_toolbar, "Open", self.open_file)
        add_btn(self.left_toolbar, "Save", self.save_file)
        add_btn(self.left_toolbar, "Save As", self.save_as_file)

        # Edit Operations (Cut, Copy, Paste, Undo, Redo, Find)
        add_btn(self.left_toolbar, "Undo", self.text_edit_undo)
        add_btn(self.left_toolbar, "Redo", self.text_edit_redo)
        add_btn(self.left_toolbar, "Cut", self.text_cut)
        add_btn(self.left_toolbar, "Copy", self.text_copy)
        add_btn(self.left_toolbar, "Paste", self.text_paste)
        add_btn(self.left_toolbar, "Find", self.find_text)

        # Formatting Operations
        add_btn(self.left_toolbar, "B", lambda: self.toggle_tag("bold"))
        add_btn(self.left_toolbar, "I", lambda: self.toggle_tag("italic"))
        add_btn(self.left_toolbar, "U", lambda: self.toggle_tag("underline"))
        add_btn(self.left_toolbar, "• List", self.insert_bullet_point)

        # Theme Toggle Button (Icon only, far right)
        self.theme_btn = add_btn(self.right_toolbar, "☀️" if self.is_dark_mode else "🌙", self.toggle_theme, padx=8)

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

    def text_cut(self):
        try:
            self.text_area.event_generate("<<Cut>>")
        except tk.TclError:
            pass

    def text_copy(self):
        try:
            self.text_area.event_generate("<<Copy>>")
        except tk.TclError:
            pass

    def text_paste(self):
        try:
            self.text_area.event_generate("<<Paste>>")
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
        self.update_line_numbers()

    def update_line_numbers(self, event=None):
        self.line_numbers.delete("all")
        
        # Determine current styling based on theme
        if self.is_dark_mode:
            num_fg = "#858585"
            num_bg = "#1e1e1e"
        else:
            num_fg = "#707070"
            num_bg = "#f0f0f0"

        self.line_numbers.config(bg=num_bg)

        # Iterate over visible lines in the text widget
        i = self.text_area.index("@0,0")
        while True:
            dline = self.text_area.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            line_num = str(i).split(".")[0]
            self.line_numbers.create_text(35, y, anchor="ne", text=line_num, fill=num_fg, font=self.normal_font)
            i = self.text_area.index(f"{i}+1line")

    def on_text_modified(self, event=None):
        if self.text_area.edit_modified():
            if self.content_saved:
                self.content_saved = False
                self.update_title()
        self.text_area.edit_modified(False)
        self.update_line_numbers()

    def update_title(self):
        display_name = self.file_path if self.file_path else "Untitled"
        prefix = "*" if not self.content_saved else ""
        self.root.title(f"{prefix}{display_name} - Nuxpad")

    def check_save_changes(self):
        if not self.content_saved:
            response = messagebox.askyesnocancel("Nuxpad", "Do you want to save changes?")
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
            self.update_line_numbers()
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
                    self.update_line_numbers()
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
        self.save_theme_preference()
        self.apply_theme()
        self.update_line_numbers()

    def apply_theme(self):
        if self.is_dark_mode:
            bg_color = "#1e1e1e"
            fg_color = "#d4d4d4"
            insert_color = "#ffffff"
            toolbar_bg = "#1e1e1e"
            btn_bg = "#2d2d2d"
            btn_fg = "#d4d4d4"
            btn_active_bg = "#3f3f46"
            select_bg = "#264f78"
            if hasattr(self, 'theme_btn'):
                self.theme_btn.config(text="☀️")
        else:
            bg_color = "#ffffff"
            fg_color = "#000000"
            insert_color = "#000000"
            toolbar_bg = "#ffffff"
            btn_bg = "#f0f0f0"
            btn_fg = "#000000"
            btn_active_bg = "#e0e0e0"
            select_bg = "#accced"
            if hasattr(self, 'theme_btn'):
                self.theme_btn.config(text="🌙")

        self.root.config(bg=bg_color)
        self.toolbar.config(bg=toolbar_bg)
        self.left_toolbar.config(bg=toolbar_bg)
        self.right_toolbar.config(bg=toolbar_bg)
        self.editor_frame.config(bg=bg_color)

        self.text_area.config(
            bg=bg_color,
            fg=fg_color,
            insertbackground=insert_color,
            selectbackground=select_bg
        )

        for btn in self.buttons:
            btn.config(bg=btn_bg, fg=btn_fg, activebackground=btn_active_bg, activeforeground=fg_color)

if __name__ == "__main__":
    root = tk.Tk()
    app = Nuxpad(root)
    root.mainloop()