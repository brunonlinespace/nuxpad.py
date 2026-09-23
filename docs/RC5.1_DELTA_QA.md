# Nuxpad 2.0.0-rc5.1 — Delta QA

## Windows identity and configuration

- [ ] About reports 2.0.0-rc5.1
- [ ] Preferences reside at:
      `%APPDATA%\brunonlinespace\Nuxpad2\nuxpad.json`
- [ ] Existing mixed-case-path preferences are retained
- [ ] Explorer displays the corrected organisation spelling
- [ ] Executable Properties shows CompanyName `brunonlinespace`
- [ ] New Windows-generated executable metadata uses `brunonlinespace`

## List button

- [ ] Toolbar displays the complete `• List` label
- [ ] No clipping at 100%, 125%, 150%, or 200% scaling
- [ ] Ctrl+L and button insertion still work
- [ ] `† Symbols` remains unchanged
- [ ] All four layouts remain aligned

## AppImage icon contrast

- [ ] Dark mode menu icons are clearly visible and light
- [ ] Light mode menu icons are clearly visible and dark
- [ ] Search/Previous/Next icons match the selected theme
- [ ] View → Dark Mode refreshes icons immediately
- [ ] `--appimage-theme=system` keeps untinted generic icons
- [ ] Portable Linux and Windows remain host-themed

## Retained checks

- [ ] More Symbols works on Linux AppImage and Windows
- [ ] External-change protection works on both systems
- [ ] Encoding, BOM, line endings, printing, and independent windows remain sound
- [ ] AppImage and Windows checksums/build records are generated
