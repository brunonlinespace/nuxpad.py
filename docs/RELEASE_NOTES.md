# Nuxpad 2.0.0-rc5.1

## Windows identity

The Windows organisation and executable CompanyName are now:

```text
brunonlinespace
```

The configuration path is:

```text
%APPDATA%\brunonlinespace\Nuxpad2\nuxpad.json
```

Nuxpad migrates the prior `BrunoOnlineSpace` directory spelling and preserves
the existing `nuxpad.json` settings.

Windows itself creates MuiCache entries for executable paths. Newly built RC5.1
executables expose the corrected lowercase company metadata. Old cache entries
for earlier build folders may remain until Windows removes them; Nuxpad does
not delete user registry data.

## Toolbar List control

The button now reads:

```text
• List
```

The platform-dependent list icon and narrow fixed width were removed, fixing
the Windows `Lis` truncation while preserving Ctrl+L and list insertion.

## AppImage icon contrast

AppImage menu and persistent search icons are rendered as light monochrome
icons in dark mode and dark monochrome icons in light mode. They refresh
immediately when View → Dark Mode changes.

Portable Linux and Windows remain host-themed.
