# Nuxpad 2 — Final critical audit

## Scope

Reviewed the canonical 2.0.0-rc1 source, Portable launcher, desktop metadata,
AppDir template, Fedora build script, assets, licence, and release documents.

## Confirmed release blockers corrected in rc2

1. **Multiple command-line files**
   The desktop file declared `%F`, but `main()` processed only `sys.argv[1]`.
   rc2 opens every valid file remaining after Qt processes its options.

2. **Save As failure state**
   rc1 changed `self.file_path` before writing and did not restore it after a
   failure. The visible title could remain stale while future saves targeted a
   different path. rc2 rolls back the path and refreshes the title/status bar.

3. **Line-ending preservation**
   rc1 preserved encoding and BOM but did not retain CRLF or CR because Qt's
   internal plain-text representation uses LF. rc2 records the predominant
   decoded style and reapplies it while saving.

4. **Predictable temporary files**
   Fixed `.nuxpad-tmp` and `.tmp` names could collide with existing files or
   links. rc2 uses securely generated temporary files in the destination
   directory and retains atomic replacement for ordinary files.

5. **Obsolete appimagetool source**
   The rc1 builder downloaded from the obsolete AppImageKit repository. rc2
   uses the current AppImage/appimagetool project and can verify a caller-
   supplied approved SHA-256.

## Packaging and polish corrections

- Dedicated About artwork is now used.
- `QApplication.setDesktopFileName("nuxpad")` aligns the window with the desktop
  entry.
- Portable execution no longer creates a source-tree symlink.
- PyInstaller's PyQt6 hooks are used without `--collect-all PyQt6`.
- Exact resolved Python packages and build-tool hashes are recorded.
- The AppDir now has a conventional `usr/bin/nuxpad` entry.
- Corrected command-substitution logging so the downloaded tool path remains valid.
- Corrected smoke-test status handling so timeout-as-success is interpreted accurately.
- Public documentation no longer presents unpublished 2.3.x versions as public
  releases or references the old configuration path.

## Security posture

No network client, plugin loader, shell command execution, `eval`, `exec`,
pickle deserialization, telemetry, update checker, or remote content execution
was found. External character-map launching uses fixed executable names resolved
through the system path and passes an argument list without a shell.

The remaining risk surface is local file editing: permissions, filesystem
behaviour, very large documents, and external modifications while a document is
open.

## Known non-blocking technical boundaries

- Saving through a symbolic link writes the target directly to preserve the
  link; this path is not atomic.
- Atomic replacement preserves standard permission bits but not every possible
  ACL, extended attribute, hard-link relationship, or unusual filesystem
  metadata.
- Find now bounds stored/highlighted results at 10,000; Replace All may still
  take time on an exceptionally large number of replacements.
- The status-bar character count follows Qt's efficient document character
  count and may count some supplementary Unicode characters as two UTF-16 code
  units.
- External-change conflicts are now checked immediately before Save; Nuxpad
  does not continuously monitor files while they remain open.
- AppImage compatibility remains dependent on building on a sufficiently old
  target baseline and testing on every declared platform.

These are documented implementation boundaries rather than known data-loss
defects. The two pressing risks identified in the review were mitigated in
2.0.0-rc5.1.

## RC4 reliability corrections

- Added pre-save external-change conflict detection with Reload, Save As,
  Overwrite, and Cancel choices.
- Bounded retained and highlighted Find matches at 10,000.
- Corrected the Ubuntu target entry to 24.04 LTS and removed the typo note.

## RC4 robustness corrections

- Replaced creator-owned child-window lists with a process-level registry of
  every open top-level editor window.
- Reduced the synchronous file-opening ceiling to 25 MiB.
- Removed the `exists()`/`stat()` race from ordinary-file permission lookup.
- Rechecked that these changes do not alter search, encoding, printing,
  external-change protection, or the feature-freeze boundary.
