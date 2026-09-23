# Nuxpad 2.0.0-rc5.1 — Cross-platform release candidate

## RC5.1 corrections

- Windows company and organisation identity is exactly `brunonlinespace`.
- Windows preferences use:
  `%APPDATA%\brunonlinespace\Nuxpad2\nuxpad.json`
- The earlier `BrunoOnlineSpace` directory is migrated to the correct spelling
  where possible.
- The toolbar control is now `• List`, with no theme icon or narrow forced
  width.
- AppImage icons are automatically tinted for contrast in dark and light mode.
- Portable Linux and Windows retain host-controlled styling and icons.

## One shared source

```text
source/nuxpad.py
```

## Configuration

Linux:

```text
~/.config/brunonlinespace/nuxpad2/nuxpad.json
```

Windows:

```text
%APPDATA%\brunonlinespace\Nuxpad2\nuxpad.json
```
