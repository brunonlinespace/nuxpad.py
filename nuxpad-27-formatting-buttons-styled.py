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
# Version: 27 (Formatting Buttons Styled)
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
        self.load_preferences()

        # Window Setup
        self.root.title("Untitled - Nuxpad")
        self.root.geometry("800x550")

        # Base Font Configuration
        self.base_font_family = "Arial"
        self.base_font_size = 11
        self.normal_font = font.Font(family=self.base_font_family, size=self.base_font_size)

        # Specialized Fonts for Toolbar Formatting Actions
        self.bold_btn_font = font.Font(family=self.base_font_family, size=self.base_font_size, weight="bold")
        self.italic_btn_font = font.Font(family=self.base_font_family, size=self.base_font_size, slant="italic")
        self.underline_btn_font = font.Font(family=self.base_font_family, size=self.base_font_size, underline=True)

        # Toolbar Frame (Container for buttons) - Placed at the BOTTOM, bezel-less
        self.toolbar = tk.Frame(self.root, bd=0, relief="flat")
        self.toolbar.pack(side="bottom", fill="x", padx=5, pady=5)

        # Main Editor Container Frame
        self.editor_frame = tk.Frame(self.root, bd=0, relief="flat")
        self.editor_frame.pack(side="top", fill="both", expand=True)

        # Line Numbers Canvas (No border/highlight)
        self.line_numbers = tk.Canvas(self.editor_frame, width=45, bd=0, highlightthickness=0)
        if self.show_line_numbers:
            self.line_numbers.pack(side="left", fill="y")

        # Text Widget & Scrollbar Container (Zero border/highlight to blend seamlessly)
        wrap_mode = "word" if self.word_wrap else "none"
        self.text_area = tk.Text(self.editor_frame, wrap=wrap_mode, undo=True, font=self.normal_font, relief="flat", bd=0, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.text_area, command=self.text_area.yview)
        
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

        # Build Toolbar Components
        self.create_toolbar()

        # Window close protocol handler
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        # Apply initial theme based on loaded preferences
        self.apply_theme()
        self.update_line_numbers()

    def load_preferences(self):
        # Defaults
        self.is_dark_mode = False
        self.word_wrap = True
        self.show_line_numbers = True

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.is_dark_mode = data.get("dark_mode", False)
                    self.word_wrap = data.get("word_wrap", True)
                    self.show_line_numbers = data.get("show_line_numbers", True)
        except Exception:
            pass

    def save_preferences(self):
        try:
            data = {
                "dark_mode": self.is_dark_mode,
                "word_wrap": self.word_wrap,
                "show_line_numbers": self.show_line_numbers
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
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
        self.root.bind("<Control-S>", lambda event: self.save_as_file())
        self.root.bind("<Control-f>", lambda event: self.find_text())
        self.root.bind("<Control-a>", lambda event: self.select_all_text())

    def create_toolbar(self):
        self.buttons = []
        self.menus = []
        self.separators = []

        # Left Frame for Menus & Formatting Tools
        self.left_toolbar = tk.Frame(self.toolbar, bd=0, relief="flat")
        self.left_toolbar.pack(side="left", anchor="w")

        # Right Frame for Search
        self.right_toolbar = tk.Frame(self.toolbar, bd=0, relief="flat")
        self.right_toolbar.pack(side="right", anchor="e")

        # --- Uniform Menubutton Helper for Dropdowns ---
        def create_menu_style_button(parent, text):
            mb = tk.Menubutton(parent, text=text, relief="flat", bd=0, padx=6, pady=2, cursor="hand2", direction="above")
            menu = tk.Menu(mb, tearoff=0)
            mb.config(menu=menu)
            mb.pack(side="left", padx=2, pady=2)
            self.buttons.append(mb)
            self.menus.append(menu)
            return menu

        # --- Uniform Button Helper for Action Items (Bold, Italic, Underline, List, Search) ---
        def create_action_button(parent, text, command, custom_font=None):
            btn = tk.Button(parent, text=text, relief="flat", bd=0, padx=6, pady=2, cursor="hand2", command=command)
            if custom_font:
                btn.config(font=custom_font)
            btn.pack(side="left", padx=2, pady=2)
            self.buttons.append(btn)
            return btn

        # --- File Menu ---
        file_menu = create_menu_style_button(self.left_toolbar, "File ▾")
        file_menu.add_command(label="📄  New               Ctrl+N", command=self.new_file)
        file_menu.add_command(label="📂  Open              Ctrl+O", command=self.open_file)
        file_menu.add_command(label="💾  Save              Ctrl+S", command=self.save_file)
        file_menu.add_command(label="💾  Save As           Ctrl+Shift+S", command=self.save_as_file)

        # --- Edit Menu ---
        edit_menu = create_menu_style_button(self.left_toolbar, "Edit ▾")
        edit_menu.add_command(label="↶  Undo             Ctrl+Z", command=self.text_edit_undo)
        edit_menu.add_command(label="↷  Redo             Ctrl+Y", command=self.text_edit_redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="✂  Cut              Ctrl+X", command=self.text_cut)
        edit_menu.add_command(label="📋  Copy            Ctrl+C", command=self.text_copy)
        edit_menu.add_command(label="📌  Paste           Ctrl+V", command=self.text_paste)
        edit_menu.add_separator()
        edit_menu.add_command(label="🔤  Select All       Ctrl+A", command=self.select_all_text)

        # --- Toggles Menu ---
        toggles_menu = create_menu_style_button(self.left_toolbar, "Toggles ▾")
        
        self.wrap_var = tk.BooleanVar(value=self.word_wrap)
        self.linenum_var = tk.BooleanVar(value=self.show_line_numbers)

        toggles_menu.add_checkbutton(label="Word Wrap", variable=self.wrap_var, command=self.toggle_word_wrap)
        toggles_menu.add_checkbutton(label="Line Numbers", variable=self.linenum_var, command=self.toggle_line_numbers)
        toggles_menu.add_separator()
        toggles_menu.add_command(label="Dark / Light Mode", command=self.toggle_theme)

        # --- Separator Frame ---
        sep = tk.Frame(self.left_toolbar, width=2, bd=0, relief="sunken")
        sep.pack(side="left", fill="y", padx=6, pady=4)
        self.separators.append(sep)

        # --- Left Format Buttons with Corresponding Font Styling ---
        create_action_button(self.left_toolbar, "Bold", lambda: self.toggle_tag("bold"), custom_font=self.bold_btn_font)
        create_action_button(self.left_toolbar, "Italic", lambda: self.toggle_tag("italic"), custom_font=self.italic_btn_font)
        create_action_button(self.left_toolbar, "Underline", lambda: self.toggle_tag("underline"), custom_font=self.underline_btn_font)
        create_action_button(self.left_toolbar, "List", self.insert_bullet_point)

        # --- Right Search Button ---
        create_action_button(self.right_toolbar, "Search", self.find_text)

    def select_all_text(self):
        self.text_area.tag_add("sel", "1.0", "end-1c")
        return "break"

    def toggle_word_wrap(self):
        self.word_wrap = self.wrap_var.get()
        wrap_mode = "word" if self.word_wrap else "none"
        self.text_area.config(wrap=wrap_mode)
        self.save_preferences()

    def toggle_line_numbers(self):
        self.show_line_numbers = self.linenum_var.get()
        if self.show_line_numbers:
            self.line_numbers.pack(side="left", fill="y")
            self.update_line_numbers()
        else:
            self.line_numbers.pack_forget()
        self.save_preferences()

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
        if not self.show_line_numbers:
            return

        self.line_numbers.delete("all")
        
        if self.is_dark_mode:
            num_fg = "#666666"
            base_bg = "#1e1e1e"
        else:
            base_bg = "#ffffff"
            num_fg = "#999999"

        self.line_numbers.config(bg=base_bg)

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
            response = self.custom_yesnocancel("Nuxpad", "Do you want to save changes?")
            if response is True:
                return self.save_file()
            elif response is False:
                return True
            else:
                return False
        return True

    def custom_yesnocancel(self, title, message):
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.geometry("360x140")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        if self.is_dark_mode:
            bg_color = "#252526"
            fg_color = "#d4d4d4"
            btn_bg = "#2d2d2d"
            btn_active = "#3f3f46"
        else:
            bg_color = "#f0f0f0"
            fg_color = "#000000"
            btn_bg = "#e0e0e0"
            btn_active = "#d0d0d0"

        dlg.config(bg=bg_color)
        result = [None]

        lbl = tk.Label(dlg, text=message, bg=bg_color, fg=fg_color, font=self.normal_font, wraplength=330, justify="left")
        lbl.pack(padx=20, pady=20, anchor="w")

        btn_frame = tk.Frame(dlg, bg=bg_color)
        btn_frame.pack(side="bottom", fill="x", padx=15, pady=10)

        def set_res(val):
            result[0] = val
            dlg.destroy()

        b_yes = tk.Button(btn_frame, text="Yes", width=8, bg=btn_bg, fg=fg_color, activebackground=btn_active, activeforeground=fg_color, relief="flat", command=lambda: set_res(True))
        b_no = tk.Button(btn_frame, text="No", width=8, bg=btn_bg, fg=fg_color, activebackground=btn_active, activeforeground=fg_color, relief="flat", command=lambda: set_res(False))
        b_cancel = tk.Button(btn_frame, text="Cancel", width=8, bg=btn_bg, fg=fg_color, activebackground=btn_active, activeforeground=fg_color, relief="flat", command=lambda: set_res(None))

        b_cancel.pack(side="right", padx=5)
        b_no.pack(side="right", padx=5)
        b_yes.pack(side="right", padx=5)

        dlg.wait_window()
        return result[0]

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
                    self.custom_message_box("Error", f"Could not open file:\n{e}")
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
                self.custom_message_box("Error", f"Could not save file:\n{e}")
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
        query = self.custom_input_dialog("Find", "Enter text to find:")
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
            
            match_bg = "#515c1e" if self.is_dark_mode else "yellow"
            match_fg = "#ffffff" if self.is_dark_mode else "black"
            self.text_area.tag_config("match", background=match_bg, foreground=match_fg)
            
            if matches == 0:
                self.custom_message_box("Find", "No matches found.")
        return "break"

    def custom_input_dialog(self, title, prompt):
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.geometry("320x130")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        if self.is_dark_mode:
            bg_color = "#252526"
            fg_color = "#d4d4d4"
            entry_bg = "#1e1e1e"
            entry_fg = "#d4d4d4"
            btn_bg = "#2d2d2d"
            btn_active = "#3f3f46"
        else:
            bg_color = "#f0f0f0"
            fg_color = "#000000"
            entry_bg = "#ffffff"
            entry_fg = "#000000"
            btn_bg = "#e0e0e0"
            btn_active = "#d0d0d0"

        dlg.config(bg=bg_color)
        result = [None]

        lbl = tk.Label(dlg, text=prompt, bg=bg_color, fg=fg_color, font=self.normal_font)
        lbl.pack(padx=15, pady=(15, 5), anchor="w")

        ent = tk.Entry(dlg, bg=entry_bg, fg=entry_fg, insertbackground=fg_color, font=self.normal_font, relief="flat")
        ent.pack(padx=15, fill="x", pady=5)
        ent.focus_set()

        btn_frame = tk.Frame(dlg, bg=bg_color)
        btn_frame.pack(side="bottom", fill="x", padx=15, pady=10)

        def on_ok(event=None):
            result[0] = ent.get()
            dlg.destroy()

        def on_cancel():
            dlg.destroy()

        b_ok = tk.Button(btn_frame, text="OK", width=8, bg=btn_bg, fg=fg_color, activebackground=btn_active, activeforeground=fg_color, relief="flat", command=on_ok)
        b_cancel = tk.Button(btn_frame, text="Cancel", width=8, bg=btn_bg, fg=fg_color, activebackground=btn_active, activeforeground=fg_color, relief="flat", command=on_cancel)

        b_cancel.pack(side="right", padx=5)
        b_ok.pack(side="right", padx=5)
        ent.bind("<Return>", on_ok)

        dlg.wait_window()
        return result[0]

    def custom_message_box(self, title, message):
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.geometry("300x120")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        if self.is_dark_mode:
            bg_color = "#252526"
            fg_color = "#d4d4d4"
            btn_bg = "#2d2d2d"
            btn_active = "#3f3f46"
        else:
            bg_color = "#f0f0f0"
            fg_color = "#000000"
            btn_bg = "#e0e0e0"
            btn_active = "#d0d0d0"

        dlg.config(bg=bg_color)

        lbl = tk.Label(dlg, text=message, bg=bg_color, fg=fg_color, font=self.normal_font, wraplength=270, justify="left")
        lbl.pack(padx=20, pady=20, anchor="w")

        b_ok = tk.Button(dlg, text="OK", width=8, bg=btn_bg, fg=fg_color, activebackground=btn_active, activeforeground=fg_color, relief="flat", command=dlg.destroy)
        b_ok.pack(side="bottom", pady=10)
        b_ok.focus_set()

        dlg.wait_window()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.save_preferences()
        self.apply_theme()
        self.update_line_numbers()

    def apply_theme(self):
        if self.is_dark_mode:
            bg_color = "#1e1e1e"
            fg_color = "#d4d4d4"
            insert_color = "#ffffff"
            btn_bg = "#1e1e1e"
            btn_fg = "#d4d4d4"
            btn_active_bg = "#333333"
            menu_bg = "#252526"
            menu_fg = "#d4d4d4"
            menu_active_bg = "#333333"
            menu_select_color = "#007acc"
            select_bg = "#264f78"
            sep_color = "#444444"
        else:
            bg_color = "#ffffff"
            fg_color = "#000000"
            insert_color = "#000000"
            btn_bg = "#ffffff"
            btn_fg = "#000000"
            btn_active_bg = "#e8e8e8"
            menu_bg = "#ffffff"
            menu_fg = "#000000"
            menu_active_bg = "#e8e8e8"
            menu_select_color = "#000000"
            select_bg = "#accced"
            sep_color = "#cccccc"

        self.root.config(bg=bg_color)
        self.toolbar.config(bg=bg_color)
        self.left_toolbar.config(bg=bg_color)
        self.right_toolbar.config(bg=bg_color)
        self.editor_frame.config(bg=bg_color)

        self.text_area.config(
            bg=bg_color,
            fg=fg_color,
            insertbackground=insert_color,
            selectbackground=select_bg
        )

        for btn in self.buttons:
            btn.config(bg=btn_bg, fg=btn_fg, activebackground=btn_active_bg, activeforeground=fg_color)

        for menu in self.menus:
            menu.config(
                bg=menu_bg, 
                fg=menu_fg, 
                activebackground=menu_active_bg, 
                activeforeground=menu_fg,
                selectcolor=menu_select_color
            )

        for sep in self.separators:
            sep.config(bg=sep_color)

if __name__ == "__main__":
    root = tk.Tk()
    app = Nuxpad(root)
    root.mainloop()