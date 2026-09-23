# Nuxpad 2.0.0-rc4-xp2 — Windows experimental QA

## Launch and identity

- [Y] Build succeeds on Windows x64
- [Y] `Nuxpad.exe` launches without a system PyQt6 installation
- [Y] About shows `2.0.0-rc4-xp2`
- [Y] Nuxpad icon appears in the title bar and taskbar
- [Y] Multiple Nuxpad windows group correctly in the taskbar

## Configuration

- [Y] Preferences are created at:
      `%APPDATA%\BrunoOnlineSpace\Nuxpad2\nuxpad.json`
- [Y] A malformed preference file does not prevent launch
- [Y] Layout, font, status bar, drag/drop, and print settings persist

## File behaviour

- [Y] New, Open, Save, Save As, Rename, and New Window
- [Y] Multiple command-line files open in separate windows
- [Y] Drag and drop works
- [N] External-change warning works
- [?] Encoding, BOM, and line endings remain preserved
- [Y] Windows-1252 opens and saves correctly
- [Y] 25 MiB opening limit works
- [Y] Long paths and paths containing spaces work

## Editing and interface

- [Y] Search, Replace, Go To Line, and 10,000-match cap
- [Y] All four layouts
- [Y] Menu Only and Status Bar toggles
- [Y] Keyboard shortcuts
- [Y] Symbols popup
- [Y] More Symbols opens Windows Character Map

## Printing

- [Y] Page Setup opens
- [?] Print to Microsoft Print to PDF - Printed small fine, but broke at 25MB
- [Y] Multi-page output
- [Y] Headers, footers, and placeholders
- [Y] No clipping or overlap

## Packaging

- [Y] Portable ZIP extracts and launches from another folder
- [Y] Portable ZIP launches on a second Windows system
- [?] SHA-256 matches
- [Y] No source `.py` file is included in the frozen application folder
- [N] No installer or registry changes are made

The AppImage-only QSS files are not included in Windows runtime behaviour; Windows continues to use its normal Qt style.
