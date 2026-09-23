# Nuxpad 2.0.0-rc5.1 — Final QA Checklist

## Launch and configuration

- [ ] Launch from source on the primary Fedora test system
- [ ] Confirm About shows version 2.0.0-rc1
- [ ] Confirm configuration is written to:
      `~/.config/brunonlinespace/nuxpad2/nuxpad.json`
- [ ] Confirm migration from older configuration locations
- [ ] Confirm a malformed config does not prevent launch

## File operations

- [ ] New
- [ ] Open
- [ ] Save
- [ ] Save As adds `.txt` only when no extension was entered
- [ ] Rename updates the on-disk file, title bar, and status bar
- [ ] Rename refuses folder paths
- [ ] Rename replacement confirmation works
- [ ] Unsaved-change Save / Discard / Cancel prompts work
- [ ] New Window works
- [ ] Multiple command-line files open correctly

## Drag and drop

- [ ] Active-window mode with a saved document
- [ ] Active-window mode with unsaved changes
- [ ] New-window mode leaves the active document untouched
- [ ] Multiple dropped files
- [ ] Unsupported or binary files are rejected safely

## Editing and shortcuts

- [ ] Undo: Ctrl+Z
- [ ] Redo: Ctrl+Y
- [ ] Cut / Copy / Paste / Select All
- [ ] List: Ctrl+L
- [ ] Rename: Ctrl+Alt+R
- [ ] Date: Ctrl+D
- [ ] Time: Ctrl+T
- [ ] Date + Time: F5
- [ ] Find: Ctrl+F
- [ ] Go To Line: Ctrl+G
- [ ] Replace: Ctrl+H
- [ ] Keyboard Shortcuts dialog matches actual bindings

## Interface

- [ ] All four layouts
- [ ] Menu Only on and off
- [ ] Status Bar on and off
- [ ] Full path appears on the left of the status bar
- [ ] Counters update on the right
- [ ] Line-number gutter keeps the Qt UI font
- [ ] User font changes affect only document text
- [ ] Symbols popup inserts characters and restores focus
- [ ] More Symbols opens an available character-map utility
- [ ] View menu spacing and labels are correct

## Encoding and content safety

- [ ] UTF-8 without BOM
- [ ] UTF-8 with BOM
- [ ] UTF-16 LE/BE
- [ ] UTF-32 LE/BE
- [ ] Windows-1252 fallback
- [ ] ISO-8859-1 fallback
- [ ] Original BOM is preserved
- [ ] Original encoding is preserved
- [ ] Unrepresentable characters cancel saving safely
- [ ] Symlink and permission behaviour remains correct
- [ ] Large-file opening remains acceptable

## `.LOG`

- [ ] First line exactly `.LOG` appends a timestamp on open
- [ ] Similar text does not trigger `.LOG`
- [ ] Timestamp uses the system locale
- [ ] Document is marked modified but not auto-saved

## Printing and PDF

- [ ] Small document prints to PDF
- [ ] Multi-page document prints to PDF
- [ ] Body text is solid black
- [ ] Header and footer do not overlap body text
- [ ] Left, centre, and right fields align correctly
- [ ] All placeholders expand correctly
- [ ] Header/footer enable toggles work
- [ ] Page Setup preferences persist

## Cross-desktop release testing

- [ ] KDE Plasma Wayland
- [ ] GNOME Wayland
- [ ] XFCE/X11
- [ ] System without PyQt6 installed — after AppImage build
- [ ] Desktop launcher icon
- [ ] Open With Nuxpad
- [ ] `%F` multiple-file desktop handling
- [ ] Printing from the packaged build

## Release gate

- [ ] No known crash
- [ ] No known data-loss bug
- [ ] README updated
- [ ] CHANGELOG updated
- [ ] GPLv3 licence included
- [ ] AppImage built
- [ ] AppImage SHA-256 generated
- [ ] GitHub release draft prepared
