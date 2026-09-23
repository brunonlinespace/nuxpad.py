# Nuxpad 2.0.0-rc4-xp2 — Windows experimental QA

## Launch and identity

- [ ] Build succeeds on Windows x64
- [ ] `Nuxpad.exe` launches without a system PyQt6 installation
- [ ] About shows `2.0.0-rc4-xp2`
- [ ] Nuxpad icon appears in the title bar and taskbar
- [ ] Multiple Nuxpad windows group correctly in the taskbar

## Configuration

- [ ] Preferences are created at:
      `%APPDATA%\BrunoOnlineSpace\Nuxpad2\nuxpad.json`
- [ ] A malformed preference file does not prevent launch
- [ ] Layout, font, status bar, drag/drop, and print settings persist

## File behaviour

- [ ] New, Open, Save, Save As, Rename, and New Window
- [ ] Multiple command-line files open in separate windows
- [ ] Drag and drop works
- [ ] External-change warning works
- [ ] Encoding, BOM, and line endings remain preserved
- [ ] Windows-1252 opens and saves correctly
- [ ] 25 MiB opening limit works
- [ ] Long paths and paths containing spaces work

## Editing and interface

- [ ] Search, Replace, Go To Line, and 10,000-match cap
- [ ] All four layouts
- [ ] Menu Only and Status Bar toggles
- [ ] Keyboard shortcuts
- [ ] Symbols popup
- [ ] More Symbols opens Windows Character Map

## Printing

- [ ] Page Setup opens
- [ ] Print to Microsoft Print to PDF
- [ ] Multi-page output
- [ ] Headers, footers, and placeholders
- [ ] No clipping or overlap

## Packaging

- [ ] Portable ZIP extracts and launches from another folder
- [ ] Portable ZIP launches on a second Windows system
- [ ] SHA-256 matches
- [ ] No source `.py` file is included in the frozen application folder
- [ ] No installer or registry changes are made

The AppImage-only QSS files are not included in Windows runtime behaviour; Windows continues to use its normal Qt style.
