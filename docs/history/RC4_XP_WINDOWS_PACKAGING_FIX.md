# Windows packaging-script correction

The original XP1 application build completed successfully, but the PowerShell
script could fail afterward while collecting PyQt6 and Qt version information.

## Cause

PowerShell interpreted the embedded `` `n `` sequence inside the Python `-c`
argument as a literal newline. Python then received an invalid one-line command.

## Correction

The script now uses two separate `print()` calls and explicitly verifies the
exit status of the Python, PyInstaller, and Qt metadata commands.

This correction changes only the Windows packaging script. The shared
application source and version remain:

```text
2.0.0-rc4-xp2
```
