# Nuxpad 2 cross-platform experiment

## Identity

Experimental version:

```text
2.0.0-rc4-xp2
```

The stable Linux RC4 source is not replaced by this experiment.

## One shared source

Linux and Windows both use:

```text
source/nuxpad.py
```

The platform-specific differences are deliberately limited to:

- preference-directory selection;
- character-map launching;
- Windows taskbar application identity;
- packaging and launch scripts;
- executable and desktop metadata.

All editor behaviour remains shared, including encoding and BOM handling,
external-change protection, multiple-window management, bounded search,
printing, `.LOG`, layouts, and the status bar.

## Configuration paths

Linux:

```text
~/.config/brunonlinespace/nuxpad2/nuxpad.json
```

Windows:

```text
%APPDATA%\BrunoOnlineSpace\Nuxpad2\nuxpad.json
```

Linux retains migration from the two unpublished historical paths. Windows has
no migration requirement because no Windows release has previously existed.

## Distribution formats

Linux:

```text
AppImage
source-portable folder
```

Windows experiment:

```text
folder-based Win32 portable package
ZIP archive
```

A Windows installer or MSIX package is intentionally deferred until the
portable experiment passes QA.

## Source rule

There is still exactly one application `.py` file in the release tree.

## Linux AppImage experiment

- Host character-map programs are launched with the bundled AppImage/PyInstaller environment removed.
- The AppImage contains optional Breeze-inspired dark and light QSS themes.
- Portable Linux and Windows appearance remain host-controlled.
