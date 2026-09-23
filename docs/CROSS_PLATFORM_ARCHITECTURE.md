# Cross-platform architecture

Nuxpad uses one shared PyQt6 application source: `source/nuxpad.py`.

Shared behaviour includes editing, layouts, encoding/BOM/line endings, atomic saves, external-change protection, search, printing, windows, drag/drop, `.LOG`, Symbols, and preferences.

Linux-specific boundaries: XDG path, desktop/AppImage packaging, host character maps, AppImage QSS themes.

Windows-specific boundaries: `%APPDATA%`, Windows Character Map, AppUserModelID/version resources, and PowerShell/PyInstaller packaging.
