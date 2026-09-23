# XP2 Windows version-check correction

The XP2 canonical source correctly declared:

```python
APP_VERSION = "2.0.0-rc4-xp2"
```

The Windows build script also set:

```powershell
$Version = "2.0.0-rc4-xp2"
```

However, its source-validation regular expression still contained the escaped
XP1 value. This caused the script to stop before building even though the
source version was correct.

The check is now generated dynamically from `$Version` using
`[regex]::Escape($Version)`. Future experimental version updates therefore
require changing only the `$Version` variable and canonical source declaration.

This is a Windows packaging-script correction only. The application remains:

```text
2.0.0-rc4-xp2
```
