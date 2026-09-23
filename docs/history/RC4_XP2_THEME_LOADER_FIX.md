# XP2 theme-loader correction

The first XP2 package reached the AppImage off-screen smoke test but failed
while applying the bundled stylesheet:

```text
NameError: name 'Path' is not defined
```

The AppImage theme loader used `Path.read_text()` without importing `Path` from
Python's `pathlib` module.

The shared source now includes:

```python
from pathlib import Path
```

No application behaviour, preference format, theme design, or version number
changed. The version remains `2.0.0-rc4-xp2`.
