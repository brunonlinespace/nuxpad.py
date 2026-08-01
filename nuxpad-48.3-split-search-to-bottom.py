#!/usr/bin/env python3
# ==============================================================================
# Nuxpad - a lightweight notepad for Linux in python
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
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# nuxpad.py
# Version: 48.3 (Left-Aligned Toolbar, Top Toolbar, Bottom Search, Downward Menus)
# ==============================================================================

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, font, Toplevel

class Nuxpad:
    def __init__(self, root):
        self.root = root
        self.file_path = None
        self.content_saved = True
        
        self.config_file = os.path.expanduser("~/.nuxpad_config.json")
        self.load_preferences()

        # Window Setup
        self.root.title("Untitled - Nuxpad v48.3")
        self.root.geometry("800x550")

        # Base Font Configuration
        self.normal_font = font.Font(family=self.base_font_family, size=self.base_font_size, weight=self.base_font_weight, slant=self.base_font_slant)
        
        # Consistent UI Font for menus, search box, and controls
        self.ui_font = font.Font(family="Arial", size=10)

        # Toolbar Frame (Top Toolbar) - bezel-less
        self.toolbar = tk.Frame(self.root, bd=0, relief="flat")
        self.toolbar.pack(side="top", fill="x", padx=5, pady=5)

        # Main Editor Container Frame
        self.editor_frame = tk.Frame(self.root, bd=0, relief="flat")
        self.editor_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        # Bottom Search Bar Frame - Placed below the editor
        self.top_search_frame = tk.Frame(self.root, bd=0, relief="flat")
        self.top_search_frame.pack(side="bottom", fill="x", padx=5, pady=(0, 5))

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

        # Track text modifications and updates for line numbers and counts
        self.text_area.bind('<<Modified>>', self.on_text_modified)
        self.text_area.bind('<KeyRelease>', self.on_key_release)
        self.text_area.bind('<MouseWheel>', self.update_line_numbers)
        self.text_area.bind('<Button-1>', self.on_click)

        # Bind Core Shortcuts
        self.bind_shortcuts()

        # Build Toolbar & Top Search Components
        self.create_toolbar()
        self.create_top_search()

        # Window close protocol handler
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        # Apply initial theme based on loaded preferences
        self.apply_theme()
        self.update_line_numbers()
        self.update_status_counts()

    def load_preferences(self):
        # Defaults
        self.is_dark_mode = False
        self.word_wrap = True
        self.show_line_numbers = True
        self.show_counters = True
        self.base_font_family = "Arial"
        self.base_font_size = 11
        self.base_font_weight = "normal"
        self.base_font_slant = "roman"

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.is_dark_mode = data.get("dark_mode", False)
                    self.word_wrap = data.get("word_wrap", True)
                    self.show_line_numbers = data.get("show_line_numbers", True)
                    self.show_counters = data.get("show_counters", True)
                    self.base_font_family = data.get("font_family", "Arial")
                    self.base_font_size = data.get("font_size", 11)
                    self.base_font_weight = data.get("font_weight", "normal")
                    self.base_font_slant = data.get("font_slant", "roman")
        except Exception:
            pass

    def save_preferences(self):
        try:
            data = {
                "dark_mode": self.is_dark_mode,
                "word_wrap": self.word_wrap,
                "show_line_numbers": self.show_line_numbers,
                "show_counters": self.show_counters,
                "font_family": self.base_font_family,
                "font_size": self.base_font_size,
                "font_weight": self.base_font_weight,
                "font_slant": self.base_font_slant
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def bind_shortcuts(self):
        self.root.bind("<Control-n>", lambda event: self.new_file())
        self.root.bind("<Control-o>", lambda event: self.open_file())
        self.root.bind("<Control-s>", lambda event: self.save_file())
        self.root.bind("<Control-S>", lambda event: self.save_as_file())
        self.root.bind("<Control-f>", lambda event: self.focus_search())
        self.root.bind("<Control-a>", lambda event: self.select_all_text())

    def create_toolbar(self):
        self.buttons = []
        self.menus = []
        self.separators = []

        # Left-Aligned Frame for Menus & Toolbar Tools
        self.left_toolbar = tk.Frame(self.toolbar, bd=0, relief="flat")
        self.left_toolbar.pack(side="top", anchor="w")

        # --- Uniform Menubutton Helper for Consistent Styling (Downward flow) ---
        def create_menu_style_button(parent, text):
            mb = tk.Menubutton(parent, text=text, relief="flat", bd=0, padx=6, pady=2, cursor="hand2", direction="below")
            menu = tk.Menu(mb, tearoff=0)
            mb.config(menu=menu)
            mb.pack(side="left", padx=2, pady=2)
            self.buttons.append(mb)
            self.menus.append(menu)
            return menu

        def create_action_menubutton(parent, text, command):
            mb = tk.Menubutton(parent, text=text, relief="flat", bd=0, padx=6, pady=2, cursor="hand2", direction="below")
            mb.bind("<Button-1>", lambda e: command())
            mb.pack(side="left", padx=2, pady=2)
            self.buttons.append(mb)
            return mb

        # --- File Menu (Downward Arrow) ---
        file_menu = create_menu_style_button(self.left_toolbar, "File ▾")
        file_menu.add_command(label="📄  New               Ctrl+N", command=self.new_file)
        file_menu.add_command(label="📂  Open              Ctrl+O", command=self.open_file)
        file_menu.add_command(label="💾  Save              Ctrl+S", command=self.save_file)
        file_menu.add_command(label="💾  Save As           Ctrl+Shift+S", command=self.save_as_file)
        file_menu.add_separator()
        file_menu.add_command(label="🔠  Display Font...", command=self.open_font_dialog)

        # --- Edit Menu (Downward Arrow) ---
        edit_menu = create_menu_style_button(self.left_toolbar, "Edit ▾")
        edit_menu.add_command(label="↶  Undo             Ctrl+Z", command=self.text_edit_undo)
        edit_menu.add_command(label="↷  Redo             Ctrl+Y", command=self.text_edit_redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="✂  Cut              Ctrl+X", command=self.text_cut)
        edit_menu.add_command(label="📋  Copy            Ctrl+C", command=self.text_copy)
        edit_menu.add_command(label="📌  Paste           Ctrl+V", command=self.text_paste)
        edit_menu.add_separator()
        edit_menu.add_command(label="🔤  Select All       Ctrl+A", command=self.select_all_text)

        # --- Toggles Menu (Downward Arrow) ---
        toggles_menu = create_menu_style_button(self.left_toolbar, "Toggles ▾")
        
        self.wrap_var = tk.BooleanVar(value=self.word_wrap)
        self.linenum_var = tk.BooleanVar(value=self.show_line_numbers)
        self.counters_var = tk.BooleanVar(value=self.show_counters)

        toggles_menu.add_checkbutton(label="Word Wrap", variable=self.wrap_var, command=self.toggle_word_wrap)
        toggles_menu.add_checkbutton(label="Line Numbers", variable=self.linenum_var, command=self.toggle_line_numbers)
        toggles_menu.add_checkbutton(label="Counters", variable=self.counters_var, command=self.toggle_counters)
        toggles_menu.add_separator()
        toggles_menu.add_command(label="Dark / Light Mode", command=self.toggle_theme)

        # --- Utility Toolbar Button ---
        create_action_menubutton(self.left_toolbar, "List", self.insert_bullet_point)

        # --- Line and Character Count Status Label styled identically to buttons ---
        self.status_label = tk.Label(self.left_toolbar, text="Lines: 1   Chars: 0", relief="flat", bd=0, padx=6, pady=2)
        if self.show_counters:
            self.status_label.pack(side="left", padx=2, pady=2)
        self.buttons.append(self.status_label)

    def create_top_search(self):
        self.search_containers = []
        self.search_widgets = []

        # Search Container Frame at the Bottom
        self.search_container = tk.Frame(self.top_search_frame, relief="solid", bd=1)
        self.search_container.pack(side="left", fill="x", expand=True, padx=2, pady=2)
        self.search_containers.append(self.search_container)

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(self.search_container, textvariable=self.search_var, relief="flat", bd=0, font=self.ui_font, highlightthickness=0)
        self.search_entry.pack(side="left", padx=(6, 4), pady=4, fill="both", expand=True)
        self.search_widgets.append(self.search_entry)
        self.search_entry.bind("<Return>", lambda event: self.find_text())

        # Integrated find button / icon on the right side of the search container
        self.inline_search_btn = tk.Label(self.search_container, text="🔍 Find", relief="flat", bd=0, padx=8, pady=2, cursor="hand2")
        self.inline_search_btn.pack(side="right", fill="y")
        self.inline_search_btn.bind("<Button-1>", lambda e: self.find_text())

    def open_font_dialog(self):
        font_win = Toplevel(self.root)
        font_win.title("Display Font Settings")
        font_win.geometry("380x320")
        font_win.transient(self.root)
        font_win.grab_set()

        # Match theme colors for dialog window
        dialog_bg = "#2d2d2d" if self.is_dark_mode else "#f0f0f0"
        dialog_fg = "#d4d4d4" if self.is_dark_mode else "#000000"
        widget_bg = "#1e1e1e" if self.is_dark_mode else "#ffffff"
        widget_fg = "#d4d4d4" if self.is_dark_mode else "#000000"

        font_win.config(bg=dialog_bg)

        # Family Selection
        tk.Label(font_win, text="Font Family:", bg=dialog_bg, fg=dialog_fg, anchor="w").pack(fill="x", padx=15, pady=(15, 2))
        
        available_fonts = sorted(list(font.families()))
        family_var = tk.StringVar(value=self.base_font_family)
        
        family_frame = tk.Frame(font_win, bg=dialog_bg)
        family_frame.pack(fill="x", padx=15, pady=2)
        
        family_listbox = tk.Listbox(family_frame, height=5, exportselection=False, bg=widget_bg, fg=widget_fg, highlightthickness=0, bd=1, relief="solid")
        family_scrollbar = tk.Scrollbar(family_frame, orient="vertical", command=family_listbox.yview)
        family_listbox.config(yscrollcommand=family_scrollbar.set)
        
        family_listbox.pack(side="left", fill="both", expand=True)
        family_scrollbar.pack(side="right", fill="y")

        for f_name in available_fonts:
            family_listbox.insert(tk.END, f_name)
            if f_name.lower() == self.base_font_family.lower():
                idx = family_listbox.get(0, tk.END).index(f_name)
                family_listbox.selection_set(idx)
                family_listbox.see(idx)

        # Size & Style Options Row
        options_frame = tk.Frame(font_win, bg=dialog_bg)
        options_frame.pack(fill="x", padx=15, pady=10)

        # Size Frame
        size_frame = tk.Frame(options_frame, bg=dialog_bg)
        size_frame.pack(side="left", fill="x", expand=True)
        tk.Label(size_frame, text="Size:", bg=dialog_bg, fg=dialog_fg, anchor="w").pack(fill="x")
        size_var = tk.StringVar(value=str(self.base_font_size))
        size_spin = tk.Spinbox(size_frame, from_=6, to=72, textvariable=size_var, width=6, bg=widget_bg, fg=widget_fg, buttonbackground=dialog_bg)
        size_spin.pack(fill="x", pady=2)

        # Weight Frame
        weight_frame = tk.Frame(options_frame, bg=dialog_bg)
        weight_frame.pack(side="left", fill="x", expand=True, padx=10)
        tk.Label(weight_frame, text="Weight:", bg=dialog_bg, fg=dialog_fg, anchor="w").pack(fill="x")
        weight_var = tk.StringVar(value=self.base_font_weight)
        weight_menu = tk.OptionMenu(weight_frame, weight_var, "normal", "bold")
        weight_menu.config(bg=widget_bg, fg=widget_fg, activebackground=widget_bg, activeforeground=widget_fg, highlightthickness=0, bd=1)
        weight_menu["menu"].config(bg=widget_bg, fg=widget_fg)
        weight_menu.pack(fill="x", pady=2)

        # Slant Frame
        slant_frame = tk.Frame(options_frame, bg=dialog_bg)
        slant_frame.pack(side="left", fill="x", expand=True)
        tk.Label(slant_frame, text="Style:", bg=dialog_bg, fg=dialog_fg, anchor="w").pack(fill="x")
        slant_var = tk.StringVar(value=self.base_font_slant)
        slant_menu = tk.OptionMenu(slant_frame, slant_var, "roman", "italic")
        slant_menu.config(bg=widget_bg, fg=widget_fg, activebackground=widget_bg, activeforeground=widget_fg, highlightthickness=0, bd=1)
        slant_menu["menu"].config(bg=widget_bg, fg=widget_fg)
        slant_menu.pack(fill="x", pady=2)

        # Apply Action
        def apply_font_changes():
            try:
                selected_indices = family_listbox.curselection()
                if selected_indices:
                    self.base_font_family = family_listbox.get(selected_indices[0])
                self.base_font_size = int(size_var.get())
                self.base_font_weight = weight_var.get()
                self.base_font_slant = slant_var.get()

                self.normal_font.config(
                    family=self.base_font_family,
                    size=self.base_font_size,
                    weight=self.base_font_weight,
                    slant=self.base_font_slant
                )
                self.save_preferences()
                self.update_line_numbers()
                font_win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Invalid font parameters:\n{e}")

        btn_frame = tk.Frame(font_win, bg=dialog_bg)
        btn_frame.pack(fill="x", padx=15, pady=10)

        apply_btn = tk.Button(btn_frame, text="Apply", command=apply_font_changes, bg=widget_bg, fg=widget_fg, relief="solid", bd=1, padx=10, pady=2)
        apply_btn.pack(side="right")

        cancel_btn = tk.Button(btn_frame, text="Cancel", command=font_win.destroy, bg=widget_bg, fg=widget_fg, relief="solid", bd=1, padx=10, pady=2)
        cancel_btn.pack(side="right", padx=10)

    def focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)
        return "break"

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

    def toggle_counters(self):
        self.show_counters = self.counters_var.get()
        if self.show_counters:
            self.status_label.pack(side="left", padx=2, pady=2)
            self.update_status_counts()
        else:
            self.status_label.pack_forget()
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
        self.update_status_counts()

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

    def update_status_counts(self):
        if not self.show_counters:
            return
        content = self.text_area.get("1.0", "end-1c")
        chars = len(content)
        lines = int(self.text_area.index("end-1c").split(".")[0])
        self.status_label.config(text=f"Lines: {lines}   Chars: {chars}")

    def on_key_release(self, event=None):
        self.update_line_numbers(event)
        self.update_status_counts()

    def on_click(self, event=None):
        self.update_line_numbers(event)
        self.update_status_counts()

    def on_text_modified(self, event=None):
        if self.text_area.edit_modified():
            if self.content_saved:
                self.content_saved = False
                self.update_title()
        self.text_area.edit_modified(False)
        self.update_line_numbers()
        self.update_status_counts()

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
            self.update_status_counts()
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
                    self.update_status_counts()
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
        query = self.search_var.get()
        if query:
            idx = "1.0"
            matches = 0
            match_ranges = []
            while True:
                idx = self.text_area.search(query, idx, nocase=True, stopindex=tk.END)
                if not idx:
                    break
                last_idx = f"{idx}+{len(query)}c"
                match_ranges.append((idx, last_idx))
                idx = last_idx
                matches += 1
            
            for start, end in match_ranges:
                self.text_area.tag_add("match", start, end)
            
            self.text_area.tag_config("match", background="yellow", foreground="black")
            
            if matches == 0:
                messagebox.showinfo("Find", "No matches found.")
        return "break"

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
            entry_bg = "#2d2d2d"
            entry_fg = "#d4d4d4"
            entry_border = "#555555"
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
            entry_bg = "#ffffff"
            entry_fg = "#000000"
            entry_border = "#7f7f7f"

        self.root.config(bg=bg_color)
        self.toolbar.config(bg=bg_color)
        self.top_search_frame.config(bg=bg_color)
        self.left_toolbar.config(bg=bg_color)
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

        for container in self.search_containers:
            container.config(bg=entry_bg, highlightbackground=entry_border, highlightcolor=entry_border)

        for entry in self.search_widgets:
            entry.config(bg=entry_bg, fg=entry_fg, insertbackground=insert_color)

        self.inline_search_btn.config(bg=entry_bg, fg=entry_fg, activebackground=entry_bg, activeforeground=entry_fg)

if __name__ == "__main__":
    root = tk.Tk()
    app = Nuxpad(root)
    root.mainloop()
