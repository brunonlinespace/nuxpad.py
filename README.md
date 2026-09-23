<p align="center">
  <a href="https://github.com/brunonlinespace/nuxpad.py">
    <img
      src="assets/icons/nuxpad-about.png"
      alt="Nuxpad 2"
      width="256"
    >
  </a>
</p>

# Nuxpad 2

**Simple. Fast. Focused.**

Nuxpad 2 is a lightweight plain-text editor for Linux and Windows, built with Python and PyQt6 from one shared source. It focuses on ordinary text files, fast editing, straightforward navigation, and careful preservation of file encoding and line endings without introducing a private document format.

Current release candidate: **2.0.0-rc5.1**

Repository: <https://github.com/brunonlinespace/nuxpad.py>

## What Nuxpad is

Nuxpad is designed as a small, direct text editor rather than a rich-text or workspace application. Documents remain ordinary files on disk and can be opened, edited, renamed, printed, or passed to Nuxpad from the command line.

Nuxpad accepts regular text files up to **25 MiB**. Binary-looking files are rejected rather than loaded into the editor.

Save As defaults extensionless names to `.txt`, while explicit extensions such as `.log`, `.md`, `.json`, or `.py` are preserved.

## Highlights

- Lightweight **plain-text editing** using Qt's plain-text editor.
- One shared application source for **Linux and Windows**.
- **New, Open, Save, Save As, Rename, Print, and New Window** workflows.
- Multiple command-line files open in independent Nuxpad windows.
- Configurable **drag and drop**: open on the active window or in new windows.
- **Word Wrap** and **Line Numbers**.
- Native **Status Bar** with the current file path plus live Lines and Chars counters.
- Four configurable interface layouts for toolbar and search placement.
- **Menu Only** mode for using the native application menu bar instead of toolbar menu buttons.
- Case-insensitive **Find** with highlighted matches, previous/next navigation, and a 10,000-match display cap.
- **Replace** and **Replace All**, with optional case matching.
- **Go To Line**.
- `• List` insertion for simple plain-text bullet lists.
- Curated **Symbols** popup plus access to the operating system's character-map utility.
- **Date**, **Time**, and **Date + Time** insertion.
- Classic Notepad-style **`.LOG`** timestamp behavior.
- Preservation of detected **encoding, BOM, and predominant line endings** when saving.
- Atomic ordinary-file saves with secure temporary files.
- SHA-256 based detection of files changed externally before Nuxpad overwrites them.
- Configurable print-only **headers and footers** with filename, page, date, time, application, and confidentiality placeholders.
- Linux AppImage-only **Dark / Light** Breeze-inspired styling.
- Windows continues to use its normal host Qt appearance.

## Interface

Nuxpad keeps its command structure intentionally compact:

**File · Edit · View · Help**

### File

- **New**
- **Open…**
- **Save**
- **Save As…**
- **Rename…**
- **Page Setup…**
- **Print…**
- **New Window**
- **Exit**

### Edit

- **Undo**
- **Redo**
- **Cut**
- **Copy**
- **Paste**
- **Date**
- **Time**
- **Date + Time**
- **Select All**
- **Go To Line…**
- **Replace…**

Find is available directly from the search field and with **Ctrl+F**.

### View

- **Word Wrap**
- **Line Numbers**
- **Menu Only**
- **Status Bar**
- **Layout**
  - Inline — Top
  - Inline — Bottom
  - Split — Toolbar Up / Search Down
  - Split — Toolbar Down / Search Top
- **Behaviour**
  - Drag and drop opens on active window
  - Drag and drop opens on new window
- **Dark Mode** — Linux AppImage only
- **Font…**

### Help

- **Keyboard Shortcuts**
- **About Nuxpad**

The main editing surface also provides dedicated **`• List`** and **`† Symbols`** buttons.

## Search and replace

The main Find field performs a literal, case-insensitive search and highlights every retained match without moving the editing cursor.

- **Previous** and **Next** move through the retained matches and wrap at the ends.
- Nuxpad retains and highlights up to **10,000** matches to keep extreme searches bounded.
- Editing the document clears the current search results so stale highlights are not left behind.
- **Replace…** is a separate modeless dialog with Replace, Replace All, and **Match case**.

## Plain-text file handling

Nuxpad opens UTF-8 directly and recognises BOM-marked:

- UTF-8
- UTF-16 LE / BE
- UTF-32 LE / BE

For non-UTF-8 text without a BOM, Nuxpad can ask the user to choose:

- Windows-1252
- ISO-8859-1
- UTF-16 LE
- UTF-16 BE
- the system encoding

When a document is saved, Nuxpad preserves its detected encoding and BOM. It also preserves the predominant original line-ending style:

- LF
- CRLF
- CR

If newly entered text cannot be represented in the document's existing encoding, Nuxpad cancels the save rather than silently replacing characters.

## Safe saving and external changes

Ordinary files are saved through a secure temporary file followed by replacement of the original file. Existing standard permission bits are retained where supported.

Symbolic links are deliberately written through so the link itself remains intact.

Nuxpad records a SHA-256 signature of the exact file bytes it opened or last wrote. Before saving over an existing document, it checks the disk copy again. When the file has changed externally, Nuxpad offers:

- **Reload**
- **Save As…**
- **Overwrite**
- **Cancel**

This protects against blindly overwriting another program's changes.

## Drag and drop

Nuxpad accepts local files dropped into the application.

**View → Behaviour** chooses between:

- **Drag and drop opens on active window**
- **Drag and drop opens on new window**

In active-window mode, Nuxpad uses the normal unsaved-changes prompt before replacing the current document. When several accepted files are dropped together, the first uses the active window and the remaining files open in new windows.

Files that fail Nuxpad's regular-file, size, or text checks are skipped.

## Lists, symbols, dates, and `.LOG`

### List

**`• List`** inserts a plain-text bullet:

- an empty line becomes `• `;
- an existing bullet item creates the next bullet;
- a normal paragraph receives `• ` at its beginning.

### Symbols

The **`† Symbols`** popup contains a curated set of common symbols. **More Symbols…** opens an available host character-map application:

- Windows: **Character Map**
- Linux: **KCharSelect**, **GNOME Characters**, **Gucharmap**, or another supported `charmap` command when available

### Date and time

Nuxpad can insert the system-local:

- date;
- time;
- date and time.

### `.LOG`

When the first line of an opened document is exactly:

```text
.LOG
```

Nuxpad appends a locale-aware date-and-time stamp at the end of the document, marks the document modified, and leaves it ready for typing. The file is not auto-saved.

## Printing

Nuxpad uses the native Qt print dialog.

**Page Setup…** controls optional print-only headers and footers with separate left, centre, and right fields.

Supported placeholders are:

| Placeholder | Meaning |
| --- | --- |
| `&F` | Filename |
| `&P` | Current page |
| `&N` | Total pages |
| `&D` | Date |
| `&T` | Time |
| `&A` | Application name |
| `&C` | `Confidential` |

Headers and footers affect printed output only; they are not inserted into the text document.

## Appearance

Portable Linux and Windows builds use the host Qt appearance.

The Linux AppImage additionally includes lightweight Breeze-inspired dark and light stylesheets. Use:

**View → Dark Mode**

- checked — dark AppImage theme;
- unchecked — light AppImage theme.

The AppImage theme also adjusts menu and search icon contrast for the selected light or dark appearance.

One-launch overrides are available:

```bash
./Nuxpad-2.0.0-rc5.1-x86_64.AppImage --appimage-theme=dark
./Nuxpad-2.0.0-rc5.1-x86_64.AppImage --appimage-theme=light
./Nuxpad-2.0.0-rc5.1-x86_64.AppImage --appimage-theme=system
```

## Useful keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+N` | New |
| `Ctrl+O` | Open |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+Alt+R` | Rename |
| `Ctrl+P` | Print |
| `Ctrl+Shift+N` | New Window |
| `Ctrl+Q` | Exit |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+X` | Cut |
| `Ctrl+C` | Copy |
| `Ctrl+V` | Paste |
| `Ctrl+A` | Select All |
| `Ctrl+L` | List |
| `Ctrl+D` | Date |
| `Ctrl+T` | Time |
| `F5` | Date + Time |
| `Ctrl+F` | Find |
| `Ctrl+G` | Go To Line |
| `Ctrl+H` | Replace |

The current shortcut inventory is also available from **Help → Keyboard Shortcuts**.

## Running from source

Nuxpad requires **Python 3** and **PyQt6** on the host.

Linux:

```bash
./portable/run-nuxpad.sh
```

or:

```bash
python3 source/nuxpad.py
```

Windows Command Prompt:

```bat
portable\run-nuxpad.cmd
```

Windows PowerShell:

```powershell
.\portable\run-nuxpad.ps1
```

The source-portable form uses the host Qt theme.

## Building the Linux AppImage

The RC5.1 AppImage builder targets **x86_64** and checks for **Fedora 43 or Fedora 44** by default.

```bash
chmod +x appimage/build-fedora-appimage.sh
./appimage/build-fedora-appimage.sh
```

Expected outputs include:

```text
dist/Nuxpad-2.0.0-rc5.1-x86_64.AppImage
dist/Nuxpad-2.0.0-rc5.1-x86_64.AppImage.sha256
dist/Nuxpad-2.0.0-rc5.1-x86_64.build-info.txt
dist/Nuxpad-2.0.0-rc5.1-x86_64.build-python-lock.txt
```

The builder creates an isolated Python environment, freezes the one canonical application source with PyInstaller, assembles the AppDir, validates important Qt components, performs an off-screen smoke test, and records build information.

## Building the Windows portable package

RC5.1 includes a PowerShell/PyInstaller helper for a self-contained **Windows x64** folder package.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\windows\build-windows-portable.ps1
```

The packaging format is a portable folder plus ZIP. It does not install file associations or create application registry entries.

## Configuration

Linux:

```text
~/.config/brunonlinespace/nuxpad2/nuxpad.json
```

Windows:

```text
%APPDATA%\brunonlinespace\Nuxpad2\nuxpad.json
```

Preferences include interface layout, word wrap, line numbers, status-bar visibility, drag-and-drop behaviour, editor font, print header/footer settings, and the AppImage theme choice where applicable.

## Current release-candidate targets

- Fedora 43
- Fedora 44
- Windows 11 x64

The source tree also records planned compatibility expansion separately from the current release-candidate targets.

## Scope

Nuxpad is a **plain-text editor**. It does not currently provide rich-text formatting, embedded images, PDF viewing, workspaces, tabs, syntax highlighting, Markdown preview, plugins, or project-management features.

That limited scope is intentional: Nuxpad is meant to remain a small editor for ordinary text files.

## License

Nuxpad 2 is licensed under the **GNU General Public License v3.0 or later**.

See `LICENSE` for the complete licence text.

## Links

- Nuxpad 2: <https://github.com/brunonlinespace/nuxpad.py>
- GitHub profile: <https://github.com/brunonlinespace/>

Copyright © 2026 Bruno Machado.
