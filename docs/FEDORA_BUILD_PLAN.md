# Fedora 43/44 AppImage build plan

Build the first distributable candidate on Fedora 43 for the older Phase 1
baseline, then test that exact AppImage on Fedora 44.

The AppDir template contains metadata and branding only. During the build,
PyInstaller freezes the single canonical `source/nuxpad.py` into
`usr/lib/nuxpad`, and `usr/bin/nuxpad` points to the frozen executable.

Required post-build checks:

- launch without system Python or PyQt6
- KDE Plasma Wayland
- Fedora 43 and Fedora 44
- `%F` with at least three files
- desktop icon and task-switcher identity
- Open With Nuxpad
- drag and drop
- print to PDF
- external More Symbols fallback
- configuration migration
