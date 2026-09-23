#!/usr/bin/env python3
# ==============================================================================
# Nuxpad - a lightweight cross-platform text editor written with PyQt6
# Copyright (C) 2026 Bruno Machado
#
# GPLv3-or-later
#
# Version: 2.0.0-rc5.1 (Windows identity and AppImage icon corrections)
# ==============================================================================

import codecs
import json
import hashlib
import locale
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import QDateTime, QLocale, QRect, QRectF, QRegularExpression, QSize, QSizeF, Qt
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QKeySequence, QPainter, QPixmap, QTextCharFormat, QTextCursor, QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFontDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTextEdit,
    QStyle,
    QStyleFactory,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "Nuxpad 2"
APP_VERSION = "2.0.0-rc5.1"
MAX_SEARCH_MATCHES = 10_000
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MiB responsiveness limit

# Strong references to every open top-level editor window. This registry is
# independent of whichever window created another one, so closing a parent or
# intermediate window cannot cause another open document to be garbage
# collected without receiving its normal close/save prompt.
OPEN_WINDOWS = set()


def register_window(window):
    """Keep a top-level editor alive until Qt destroys that exact window."""
    OPEN_WINDOWS.add(window)
    window.destroyed.connect(
        lambda _object=None, registered=window: OPEN_WINDOWS.discard(registered)
    )


def normalise_windows_organisation_directory(appdata):
    """Migrate the earlier Windows organisation directory spelling."""
    desired_name = "brunonlinespace"
    desired_path = os.path.join(appdata, desired_name)
    legacy_names = (
        "BrunoOnlineSpace",
        "brunoonlinespace",
    )

    try:
        entries = list(os.scandir(appdata))
    except OSError:
        return desired_path

    if any(
        entry.is_dir(follow_symlinks=False)
        and entry.name == desired_name
        for entry in entries
    ):
        return desired_path

    legacy_entry = next(
        (
            entry
            for entry in entries
            if entry.is_dir(follow_symlinks=False)
            and entry.name in legacy_names
        ),
        None,
    )
    if legacy_entry is None:
        return desired_path

    # Rename through a temporary sibling. This works both for a casing-only
    # correction and for the earlier extra-"o" spelling.
    temporary_path = None
    for counter in range(100):
        candidate = os.path.join(
            appdata,
            f".nuxpad-org-migration-{os.getpid()}-{counter}",
        )
        if not os.path.exists(candidate):
            temporary_path = candidate
            break

    if temporary_path is None:
        return desired_path

    try:
        os.rename(legacy_entry.path, temporary_path)
        os.rename(temporary_path, desired_path)
    except OSError:
        try:
            if (
                os.path.exists(temporary_path)
                and not os.path.exists(legacy_entry.path)
            ):
                os.rename(temporary_path, legacy_entry.path)
        except OSError:
            pass

    return desired_path


def platform_config_locations():
    """Return the native preference path and any import candidates."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = os.path.join(
                os.path.expanduser("~"),
                "AppData",
                "Roaming",
            )
        organisation_directory = normalise_windows_organisation_directory(
            appdata
        )
        config_directory = os.path.join(
            organisation_directory,
            "Nuxpad2",
        )
        import_candidates = (
            os.path.join(
                appdata,
                "BrunoOnlineSpace",
                "Nuxpad2",
                "nuxpad.json",
            ),
            os.path.join(
                appdata,
                "brunoonlinespace",
                "Nuxpad2",
                "nuxpad.json",
            ),
        )
        return config_directory, import_candidates

    config_directory = os.path.expanduser(
        "~/.config/brunonlinespace/nuxpad2"
    )
    import_candidates = (
        os.path.expanduser("~/.config/brunonlinespace/nuxpad.json"),
        os.path.expanduser("~/.nuxpad_config.json"),
    )
    return config_directory, import_candidates


def configure_platform_identity():
    """Apply small platform-specific process identity settings."""
    if sys.platform != "win32":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "brunonlinespace.Nuxpad2"
        )
    except (AttributeError, OSError):
        # The editor remains fully usable when the Windows shell API is absent.
        pass


def host_process_environment():
    """Return a clean environment for launching host desktop applications."""
    environment = os.environ.copy()

    if sys.platform == "win32":
        return environment

    # Portable source runs should inherit the user's environment unchanged.
    if not (
        environment.get("APPDIR")
        or getattr(sys, "frozen", False)
    ):
        return environment

    appdir = environment.get("APPDIR")
    original_library_path = environment.pop(
        "LD_LIBRARY_PATH_ORIG",
        None,
    )
    if original_library_path is None:
        environment.pop("LD_LIBRARY_PATH", None)
    else:
        environment["LD_LIBRARY_PATH"] = original_library_path

    # Do not leak the bundled application's Qt/plugin configuration into a
    # character-map utility supplied by the host operating system.
    for variable in (
        "APPDIR",
        "APPIMAGE",
        "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM",
        "QT_QPA_PLATFORM_PLUGIN_PATH",
        "QT_QPA_PLATFORMTHEME",
        "QT_STYLE_OVERRIDE",
        "QML_IMPORT_PATH",
        "QML2_IMPORT_PATH",
    ):
        environment.pop(variable, None)

    if appdir and environment.get("PATH"):
        appdir_real = os.path.realpath(appdir)
        clean_path = []
        for entry in environment["PATH"].split(os.pathsep):
            if not entry:
                continue
            try:
                entry_real = os.path.realpath(entry)
                inside_appdir = os.path.commonpath(
                    (appdir_real, entry_real)
                ) == appdir_real
            except (OSError, ValueError):
                inside_appdir = False
            if not inside_appdir:
                clean_path.append(entry)
        environment["PATH"] = os.pathsep.join(clean_path)

    return environment


def appimage_theme_resources():
    """Return bundled AppImage QSS paths, or an empty mapping elsewhere."""
    appdir = os.environ.get("APPDIR")
    if not appdir:
        return {}

    style_directory = os.path.join(
        appdir,
        "usr",
        "share",
        "nuxpad",
        "styles",
    )
    resources = {
        "dark": os.path.join(style_directory, "breeze-dark.qss"),
        "light": os.path.join(style_directory, "breeze-light.qss"),
    }
    if all(os.path.isfile(path) for path in resources.values()):
        return resources
    return {}


def resource_path(*parts):
    """Return an asset path in source, portable, legacy, and AppImage layouts."""
    candidates = []
    appdir = os.environ.get("APPDIR")
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # PyInstaller places bundled data beside the frozen script location.
    candidates.append(os.path.join(script_dir, *parts))

    # The reviewed release tree keeps one source file and one shared asset tree.
    candidates.append(
        os.path.normpath(os.path.join(script_dir, "..", "assets", *parts))
    )

    # Retain compatibility with the unpublished 2.3.x development layout.
    candidates.append(os.path.join(script_dir, "nuxpad2-assets", *parts))

    if appdir:
        candidates.append(os.path.join(appdir, *parts))
        candidates.append(
            os.path.join(appdir, "usr", "share", "nuxpad", *parts)
        )

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return candidates[0]


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        # Keep the gutter on Qt's normal UI font, independent of the
        # user-selected document font.
        self.setFont(QApplication.font())

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class DropTextEdit(QPlainTextEdit):
    """Plain-text editor with line numbers and native local-file drops."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.show_line_numbers = True
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.line_number_area.update)
        self.update_line_number_area_width()

    def line_number_area_width(self):
        if not self.show_line_numbers:
            return 0
        digits = len(str(max(1, self.blockCount())))
        metrics = self.line_number_area.fontMetrics()
        return 10 + metrics.horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _=0):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        contents = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(contents.left(), contents.top(), self.line_number_area_width(), contents.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.setFont(self.line_number_area.font())
        metrics = self.line_number_area.fontMetrics()
        painter.fillRect(event.rect(), self.palette().base())
        painter.setPen(self.palette().color(self.palette().ColorRole.PlaceholderText))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 6,
                    metrics.height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def set_line_numbers_visible(self, visible):
        self.show_line_numbers = bool(visible)
        self.line_number_area.setVisible(self.show_line_numbers)
        self.update_line_number_area_width()

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls() and any(url.isLocalFile() for url in mime.urls()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls() and any(url.isLocalFile() for url in mime.urls()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        files = [path for path in paths if os.path.isfile(path)]
        if files:
            window = self.window()
            if hasattr(window, "open_dropped_files"):
                window.open_dropped_files(files)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class Nuxpad(QMainWindow):
    def __init__(self, initial_file=None):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        register_window(self)

        self.file_path = None
        self.file_encoding = "utf-8"
        self.file_bom = b""
        self.file_newline = "\n"
        self.file_disk_signature = None
        self.content_saved = True
        self._loading = False
        self.replace_dialog = None
        self.search_matches = []
        self.search_results_truncated = False
        self.current_search_index = -1
        self.icon_bindings = []
        (
            self.config_directory,
            self.config_import_candidates,
        ) = platform_config_locations()
        self.config_file = os.path.join(
            self.config_directory,
            "nuxpad.json",
        )

        self.appimage_theme_files = appimage_theme_resources()
        self.appimage_theme_available = bool(self.appimage_theme_files)
        requested_theme = os.environ.get(
            "NUXPAD_APPIMAGE_THEME",
            "",
        ).strip().lower()
        self.appimage_theme_override = (
            requested_theme
            if requested_theme in ("dark", "light", "system")
            else None
        )

        self.load_preferences()
        if self.appimage_theme_available:
            self.apply_appimage_theme(
                self.effective_appimage_theme(),
                update_actions=False,
            )

        self.resize(800, 550)
        self.setMinimumSize(640, 420)
        self.setAcceptDrops(True)
        icon_path = resource_path("icons", "nuxpad.png")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.build_ui()
        self.bind_shortcuts()
        self.apply_preferences()
        self.apply_native_style()
        self.update_title()
        self.update_status_counts()
        self.update_search_counter()

        if initial_file:
            self.load_file(initial_file, check_changes=False)

    # ---------- Preferences ----------
    def load_preferences(self):
        self.word_wrap = True
        self.show_line_numbers = True
        self.show_status_bar = True
        self.use_app_menu = True
        self.layout_mode = 1
        # Default: replace the active document after the normal save prompt.
        self.drop_open_mode = "active_window"
        self.base_font_family = "Sans Serif"
        self.base_font_size = 11
        self.base_font_weight = "normal"
        self.base_font_slant = "roman"
        # This preference is used only by the Linux AppImage.
        self.appimage_theme = "dark"
        self.print_header_enabled = True
        self.print_header_left = "&F"
        self.print_header_center = ""
        self.print_header_right = ""
        self.print_footer_enabled = True
        self.print_footer_left = ""
        self.print_footer_center = "Page &P of &N"
        self.print_footer_right = ""

        # Prefer the native final path. Linux imports unpublished historical
        # locations; Windows imports the earlier organisation spelling.
        source_file = self.config_file
        migrating_legacy_config = False

        if not os.path.isfile(self.config_file):
            for candidate in self.config_import_candidates:
                if os.path.isfile(candidate):
                    source_file = candidate
                    migrating_legacy_config = True
                    break

        try:
            with open(source_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)

            self.word_wrap = bool(data.get("word_wrap", True))
            self.show_line_numbers = bool(data.get("show_line_numbers", True))
            self.show_status_bar = bool(
                data.get("show_status_bar", data.get("show_counters", True))
            )
            self.use_app_menu = bool(data.get("use_app_menu", True))

            saved_drop_mode = data.get("drop_open_mode", "active_window")
            if saved_drop_mode in ("active_window", "new_window"):
                self.drop_open_mode = saved_drop_mode

            saved_mode = data.get("layout_mode")
            if saved_mode in (1, 2, 3, 4):
                self.layout_mode = int(saved_mode)
            else:
                self.layout_mode = (
                    3 if bool(data.get("split_search", False)) else 1
                )

            self.base_font_family = data.get("font_family", "Sans Serif")
            self.base_font_size = int(data.get("font_size", 11))
            self.base_font_weight = data.get("font_weight", "normal")
            self.base_font_slant = data.get("font_slant", "roman")

            saved_appimage_theme = str(
                data.get("appimage_theme", "dark")
            ).lower()
            if saved_appimage_theme in ("dark", "light"):
                self.appimage_theme = saved_appimage_theme

            self.print_header_enabled = bool(
                data.get("print_header_enabled", True)
            )
            old_header = str(data.get("print_header_text", "&F"))
            self.print_header_left = str(
                data.get("print_header_left", old_header)
            )
            self.print_header_center = str(
                data.get("print_header_center", "")
            )
            self.print_header_right = str(
                data.get("print_header_right", "")
            )

            self.print_footer_enabled = bool(
                data.get("print_footer_enabled", True)
            )
            old_footer = str(
                data.get("print_footer_text", "Page &P of &N")
            )
            self.print_footer_left = str(
                data.get("print_footer_left", "")
            )
            self.print_footer_center = str(
                data.get("print_footer_center", old_footer)
            )
            self.print_footer_right = str(
                data.get("print_footer_right", "")
            )

        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            migrating_legacy_config = False

        if migrating_legacy_config:
            # Keep the old file untouched as a backup. Future launches use the
            # new path after this write succeeds.
            self.save_preferences()

    def save_preferences(self):
        data = {
            "word_wrap": self.word_wrap,
            "show_line_numbers": self.show_line_numbers,
            "show_status_bar": self.show_status_bar,
            # Retain the old key for compatibility with earlier builds.
            "show_counters": self.show_status_bar,
            "use_app_menu": self.use_app_menu,
            "layout_mode": self.layout_mode,
            "drop_open_mode": self.drop_open_mode,
            "font_family": self.base_font_family,
            "font_size": self.base_font_size,
            "font_weight": self.base_font_weight,
            "font_slant": self.base_font_slant,
            "print_header_enabled": self.print_header_enabled,
            "print_header_left": self.print_header_left,
            "print_header_center": self.print_header_center,
            "print_header_right": self.print_header_right,
            "print_header_text": self.print_header_left,
            "print_footer_enabled": self.print_footer_enabled,
            "print_footer_left": self.print_footer_left,
            "print_footer_center": self.print_footer_center,
            "print_footer_right": self.print_footer_right,
            "print_footer_text": self.print_footer_center,
        }
        if self.appimage_theme_available:
            data["appimage_theme"] = self.appimage_theme

        temporary = None
        descriptor = None
        try:
            os.makedirs(self.config_directory, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(
                prefix=".nuxpad-",
                suffix=".json.tmp",
                dir=self.config_directory,
                text=True,
            )
            os.chmod(temporary, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                descriptor = None
                json.dump(data, handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.config_file)
            temporary = None
        except OSError:
            pass
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if temporary:
                try:
                    os.remove(temporary)
                except OSError:
                    pass

    # ---------- UI ----------
    def build_ui(self):
        central = QWidget(self)
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(6, 6, 6, 6)
        self.main_layout.setSpacing(6)

        self.toolbar = QWidget(self)
        self.toolbar.setObjectName("toolbar")
        self.toolbar_layout = QHBoxLayout(self.toolbar)
        self.toolbar_layout.setContentsMargins(0, 0, 0, 0)
        # Keep every toolbar control in one compact row with equal spacing.
        self.toolbar_layout.setSpacing(6)
        self.main_layout.addWidget(self.toolbar)

        # Use a real Qt menu bar so KDE Plasma can expose it through
        # the desktop's global Application Menu widget.
        self.app_menu_bar = self.menuBar()
        self.app_menu_bar.clear()
        self.make_file_menu()
        self.make_edit_menu()
        self.make_view_menu()
        self.make_help_menu()

        # The same QMenu objects can be presented either through Qt's native
        # application menu bar or through ordinary click-only toolbar buttons.
        self.menu_buttons_container = QWidget(self.toolbar)
        self.menu_buttons_layout = QHBoxLayout(self.menu_buttons_container)
        self.menu_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_buttons_layout.setSpacing(6)
        self.menu_buttons_container.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Preferred,
        )
        self.menu_buttons = []
        for label, menu in (
            ("File", self.file_menu),
            ("Edit", self.edit_menu),
            ("View", self.view_menu),
            ("Help", self.help_menu),
        ):
            button = QToolButton(self.menu_buttons_container)
            button.setText(label)
            button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            button.setMenu(menu)
            self.menu_buttons_layout.addWidget(button)
            self.menu_buttons.append(button)


        # Keep menus, List, and Symbols inside one fixed, left-aligned group.
        # The outer toolbar layout sees this as one widget, so these controls can
        # never drift apart when the window grows or when a split layout hides search.
        self.primary_controls = QWidget(self.toolbar)
        self.primary_controls.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Preferred,
        )
        self.primary_controls_layout = QHBoxLayout(self.primary_controls)
        self.primary_controls_layout.setContentsMargins(0, 0, 0, 0)
        self.primary_controls_layout.setSpacing(6)
        self.primary_controls_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.primary_controls_layout.addWidget(self.menu_buttons_container)

        self.list_button = QPushButton("• List", self.primary_controls)
        self.list_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_button.clicked.connect(self.insert_bullet_point)
        self.list_button.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.primary_controls_layout.addWidget(self.list_button)

        self.symbols_button = QPushButton("† Symbols", self.primary_controls)
        self.symbols_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.symbols_button.clicked.connect(self.show_symbols_popup)
        self.symbols_button.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.primary_controls_layout.addWidget(self.symbols_button)

        self.toolbar_layout.addWidget(
            self.primary_controls,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )

        # Native bottom status bar: file path on the left, counters on the right.
        self.app_status_bar = self.statusBar()
        self.app_status_bar.setSizeGripEnabled(True)

        self.path_label = QLabel("Untitled", self.app_status_bar)
        self.path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.path_label.setToolTip("Untitled")
        self.app_status_bar.addWidget(self.path_label, 1)

        self.lines_label = QLabel("Lines: 1", self.app_status_bar)
        self.chars_label = QLabel("Chars: 0", self.app_status_bar)
        self.app_status_bar.addPermanentWidget(self.lines_label)
        self.app_status_bar.addPermanentWidget(self.chars_label)

        self.search_container = QWidget(self)
        self.search_container.setObjectName("searchContainer")
        self.search_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        search_layout = QHBoxLayout(self.search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(6)
        self.search_entry = QLineEdit(self)
        self.search_entry.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.search_entry.setPlaceholderText("Find text")
        self.search_entry.returnPressed.connect(self.find_next)
        self.search_entry.textChanged.connect(self.on_search_text_changed)
        self.search_button = QPushButton(self)
        self.bind_portable_icon(
            self.search_button,
            "edit-find",
            QStyle.StandardPixmap.SP_FileDialogContentsView,
        )
        self.search_button.setToolTip("Highlight all matches")
        self.search_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.search_button.clicked.connect(self.find_text_and_refocus)

        self.search_count_label = QLabel("0/0", self.search_container)
        self.search_count_label.setMinimumWidth(42)
        self.search_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.search_previous_button = QToolButton(self.search_container)
        self.bind_portable_icon(
            self.search_previous_button,
            "go-previous",
            QStyle.StandardPixmap.SP_ArrowBack,
        )
        self.search_previous_button.setToolTip("Previous match")
        self.search_previous_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.search_previous_button.clicked.connect(self.find_previous)

        self.search_next_button = QToolButton(self.search_container)
        self.bind_portable_icon(
            self.search_next_button,
            "go-next",
            QStyle.StandardPixmap.SP_ArrowForward,
        )
        self.search_next_button.setToolTip("Next match")
        self.search_next_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.search_next_button.clicked.connect(self.find_next)

        search_layout.addWidget(self.search_entry, 1)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.search_count_label)
        search_layout.addWidget(self.search_previous_button)
        search_layout.addWidget(self.search_next_button)
        self.toolbar_layout.addWidget(self.search_container, 1)
        self.toolbar_layout.setStretchFactor(self.search_container, 1)

        self.text_area = DropTextEdit(self)
        self.text_area.setObjectName("editor")
        self.text_area.setUndoRedoEnabled(True)
        self.text_area.document().modificationChanged.connect(self.on_modification_changed)
        self.text_area.textChanged.connect(self.on_document_text_changed)
        self.main_layout.addWidget(self.text_area, 1)

        self.bottom_search = QWidget(self)
        self.bottom_search.setObjectName("bottomSearch")
        bottom_layout = QHBoxLayout(self.bottom_search)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)
        self.bottom_search_entry = QLineEdit(self)
        self.bottom_search_entry.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.bottom_search_entry.setPlaceholderText("Find text")
        self.bottom_search_entry.returnPressed.connect(self.find_next)
        self.bottom_search_entry.textChanged.connect(self.on_search_text_changed)
        bottom_button = QPushButton("Find", self)
        self.bind_portable_icon(
            bottom_button,
            "edit-find",
            QStyle.StandardPixmap.SP_FileDialogContentsView,
        )
        bottom_button.setToolTip("Highlight all matches")
        bottom_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        bottom_button.clicked.connect(self.find_text_and_refocus)

        self.bottom_search_count_label = QLabel("0/0", self.bottom_search)
        self.bottom_search_count_label.setMinimumWidth(42)
        self.bottom_search_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.bottom_previous_button = QToolButton(self.bottom_search)
        self.bind_portable_icon(
            self.bottom_previous_button,
            "go-previous",
            QStyle.StandardPixmap.SP_ArrowBack,
        )
        self.bottom_previous_button.setToolTip("Previous match")
        self.bottom_previous_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bottom_previous_button.clicked.connect(self.find_previous)

        self.bottom_next_button = QToolButton(self.bottom_search)
        self.bind_portable_icon(
            self.bottom_next_button,
            "go-next",
            QStyle.StandardPixmap.SP_ArrowForward,
        )
        self.bottom_next_button.setToolTip("Next match")
        self.bottom_next_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bottom_next_button.clicked.connect(self.find_next)

        bottom_layout.addWidget(self.bottom_search_entry, 1)
        bottom_layout.addWidget(bottom_button)
        bottom_layout.addWidget(self.bottom_search_count_label)
        bottom_layout.addWidget(self.bottom_previous_button)
        bottom_layout.addWidget(self.bottom_next_button)
        self.main_layout.addWidget(self.bottom_search)

    @staticmethod
    def tint_icon(icon, colour):
        """Render a monochrome high-contrast copy while preserving icon alpha."""
        tinted_icon = QIcon()
        sizes = icon.availableSizes()
        if not sizes:
            sizes = (
                QSize(16, 16),
                QSize(22, 22),
                QSize(24, 24),
                QSize(32, 32),
            )

        for size in sizes:
            pixmap = icon.pixmap(size)
            if pixmap.isNull():
                continue

            tinted = QPixmap(pixmap.size())
            tinted.fill(Qt.GlobalColor.transparent)

            painter = QPainter(tinted)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceIn
            )
            painter.fillRect(tinted.rect(), colour)
            painter.end()

            tinted.setDevicePixelRatio(pixmap.devicePixelRatio())
            tinted_icon.addPixmap(tinted)

        return tinted_icon if not tinted_icon.isNull() else icon

    def portable_icon(self, theme_name, fallback):
        """Return a host icon, with AppImage-theme contrast correction."""
        icon = QIcon.fromTheme(theme_name)
        if icon.isNull():
            icon = self.style().standardIcon(fallback)

        if self.appimage_theme_available:
            theme = self.effective_appimage_theme()
            if theme == "dark":
                return self.tint_icon(icon, QColor("#eff0f1"))
            if theme == "light":
                return self.tint_icon(icon, QColor("#232629"))

        return icon

    def bind_portable_icon(self, target, theme_name, fallback):
        """Assign an icon and remember how to rebuild it after a theme change."""
        target.setIcon(self.portable_icon(theme_name, fallback))
        self.icon_bindings.append((target, theme_name, fallback))

    def refresh_portable_icons(self):
        """Rebuild all registered icons for the current AppImage theme."""
        for target, theme_name, fallback in tuple(self.icon_bindings):
            try:
                target.setIcon(self.portable_icon(theme_name, fallback))
            except RuntimeError:
                # Temporary widgets can already be deleted when a theme changes.
                continue

    def add_menu_action(self, menu, label, callback, shortcut, theme_icon, fallback_icon):
        action = QAction(label, self)
        self.bind_portable_icon(action, theme_icon, fallback_icon)
        action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(shortcut)
        menu.addAction(action)
        return action

    def make_file_menu(self):
        menu = QMenu("&File", self)
        self.file_menu = menu
        self.app_menu_bar.addMenu(menu)
        self.add_menu_action(
            menu, "New", self.new_file, QKeySequence.StandardKey.New,
            "document-new", QStyle.StandardPixmap.SP_FileIcon,
        )
        self.add_menu_action(
            menu, "Open…", self.open_file, QKeySequence.StandardKey.Open,
            "document-open", QStyle.StandardPixmap.SP_DialogOpenButton,
        )
        menu.addSeparator()
        self.add_menu_action(
            menu, "Save", self.save_file, QKeySequence.StandardKey.Save,
            "document-save", QStyle.StandardPixmap.SP_DialogSaveButton,
        )
        self.add_menu_action(
            menu, "Save As…", self.save_as_file, QKeySequence.StandardKey.SaveAs,
            "document-save-as", QStyle.StandardPixmap.SP_DialogSaveButton,
        )
        menu.addSeparator()
        self.add_menu_action(
            menu, "Rename…", self.rename_current_file, QKeySequence("Ctrl+Alt+R"),
            "edit-rename", QStyle.StandardPixmap.SP_FileDialogDetailedView,
        )
        menu.addSeparator()
        self.add_menu_action(
            menu, "Page Setup…", self.show_page_setup_dialog, None,
            "document-page-setup", QStyle.StandardPixmap.SP_FileDialogDetailedView,
        )
        self.add_menu_action(
            menu, "Print…", self.print_document, QKeySequence.StandardKey.Print,
            "document-print", QStyle.StandardPixmap.SP_DialogApplyButton,
        )
        menu.addSeparator()
        self.add_menu_action(
            menu, "New Window", self.new_window, QKeySequence("Ctrl+Shift+N"),
            "window-new", QStyle.StandardPixmap.SP_TitleBarNormalButton,
        )
        self.add_menu_action(
            menu, "Exit", self.close, QKeySequence.StandardKey.Quit,
            "application-exit", QStyle.StandardPixmap.SP_DialogCloseButton,
        )


    def make_edit_menu(self):
        menu = QMenu("&Edit", self)
        self.edit_menu = menu
        self.app_menu_bar.addMenu(menu)
        self.add_menu_action(
            menu, "Undo", self.text_area_undo, QKeySequence.StandardKey.Undo,
            "edit-undo", QStyle.StandardPixmap.SP_ArrowBack,
        )
        self.add_menu_action(
            menu, "Redo", self.text_area_redo, QKeySequence("Ctrl+Y"),
            "edit-redo", QStyle.StandardPixmap.SP_ArrowForward,
        )
        menu.addSeparator()
        self.add_menu_action(
            menu, "Cut", lambda: self.text_area.cut(), QKeySequence.StandardKey.Cut,
            "edit-cut", QStyle.StandardPixmap.SP_DialogResetButton,
        )
        self.add_menu_action(
            menu, "Copy", lambda: self.text_area.copy(), QKeySequence.StandardKey.Copy,
            "edit-copy", QStyle.StandardPixmap.SP_FileDialogListView,
        )
        self.add_menu_action(
            menu, "Paste", lambda: self.text_area.paste(), QKeySequence.StandardKey.Paste,
            "edit-paste", QStyle.StandardPixmap.SP_DialogApplyButton,
        )
        menu.addSeparator()
        self.add_menu_action(
            menu, "Date", self.insert_date, QKeySequence("Ctrl+D"),
            "view-calendar", QStyle.StandardPixmap.SP_FileDialogInfoView,
        )
        self.add_menu_action(
            menu, "Time", self.insert_time, QKeySequence("Ctrl+T"),
            "appointment-new", QStyle.StandardPixmap.SP_FileDialogInfoView,
        )
        self.add_menu_action(
            menu, "Date + Time", self.insert_time_date, QKeySequence("F5"),
            "appointment-new", QStyle.StandardPixmap.SP_FileDialogInfoView,
        )
        menu.addSeparator()
        self.add_menu_action(
            menu, "Select All", lambda: self.text_area.selectAll(),
            QKeySequence.StandardKey.SelectAll, "edit-select-all",
            QStyle.StandardPixmap.SP_DialogYesButton,
        )
        menu.addSeparator()
        self.add_menu_action(
            menu, "Go To Line…", self.go_to_line, QKeySequence("Ctrl+G"),
            "go-jump", QStyle.StandardPixmap.SP_ArrowDown,
        )
        self.add_menu_action(
            menu, "Replace…", self.show_replace_dialog, QKeySequence("Ctrl+H"),
            "edit-find-replace", QStyle.StandardPixmap.SP_BrowserReload,
        )


    def make_view_menu(self):
        menu = QMenu("&View", self)
        self.view_menu = menu
        self.app_menu_bar.addMenu(menu)
        self.wrap_action = QAction("Word Wrap", self, checkable=True)
        self.wrap_action.triggered.connect(self.toggle_word_wrap)
        menu.addAction(self.wrap_action)

        self.line_numbers_action = QAction("Line Numbers", self, checkable=True)
        self.line_numbers_action.triggered.connect(self.toggle_line_numbers)
        menu.addAction(self.line_numbers_action)

        menu.addSeparator()

        self.app_menu_action = QAction("Menu Only", self, checkable=True)
        self.app_menu_action.setToolTip(
            "Use the native application menu bar; turn off to show File, Edit, View and Help as toolbar buttons."
        )
        self.app_menu_action.triggered.connect(self.toggle_menu_style)
        menu.addAction(self.app_menu_action)

        self.status_bar_action = QAction("Status Bar", self, checkable=True)
        self.status_bar_action.setToolTip(
            "Show the current file path and live document counters."
        )
        self.status_bar_action.triggered.connect(self.toggle_status_bar)
        menu.addAction(self.status_bar_action)

        menu.addSeparator()

        layout_menu = menu.addMenu("Layout")
        self.layout_actions = {}
        layout_labels = {
            1: "Inline — Top",
            2: "Inline — Bottom",
            3: "Split — Toolbar Up / Search Down",
            4: "Split — Toolbar Down / Search Top",
        }
        for mode, label in layout_labels.items():
            action = QAction(label, self, checkable=True)
            action.triggered.connect(
                lambda _checked=False, selected=mode: self.set_layout_mode(selected)
            )
            layout_menu.addAction(action)
            self.layout_actions[mode] = action

        behaviour_menu = menu.addMenu("Behaviour")
        self.drop_behaviour_actions = {}
        behaviour_labels = {
            "active_window": "Drag and drop opens on active window",
            "new_window": "Drag and drop opens on new window",
        }
        for mode, label in behaviour_labels.items():
            action = QAction(label, self, checkable=True)
            action.triggered.connect(
                lambda _checked=False, selected=mode: self.set_drop_open_mode(selected)
            )
            behaviour_menu.addAction(action)
            self.drop_behaviour_actions[mode] = action

        menu.addSeparator()

        self.appimage_dark_mode_action = None
        if self.appimage_theme_available:
            self.appimage_dark_mode_action = QAction(
                "Dark Mode",
                self,
                checkable=True,
            )
            self.appimage_dark_mode_action.setToolTip(
                "Use the AppImage-only Breeze-inspired dark theme; "
                "turn off for light mode."
            )
            self.appimage_dark_mode_action.triggered.connect(
                self.toggle_appimage_dark_mode
            )
            menu.addAction(self.appimage_dark_mode_action)

        font_action = QAction("Font…", self)
        font_action.triggered.connect(self.open_font_dialog)
        menu.addAction(font_action)


    def make_help_menu(self):
        menu = QMenu("&Help", self)
        self.help_menu = menu
        self.app_menu_bar.addMenu(menu)

        self.add_menu_action(
            menu, "Keyboard Shortcuts", self.show_keyboard_shortcuts_dialog, None,
            "preferences-desktop-keyboard", QStyle.StandardPixmap.SP_FileDialogDetailedView,
        )
        menu.addSeparator()
        self.add_menu_action(
            menu, "About Nuxpad", self.show_about_dialog, None,
            "help-about", QStyle.StandardPixmap.SP_MessageBoxInformation,
        )
        # A native QMenuBar is required for KDE's global menu integration.

    def bind_shortcuts(self):
        find_action = QAction(self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(self.focus_search)
        self.addAction(find_action)

        list_action = QAction(self)
        list_action.setShortcut(QKeySequence("Ctrl+L"))
        list_action.triggered.connect(self.insert_bullet_point)
        self.addAction(list_action)

    def apply_preferences(self):
        self.wrap_action.setChecked(self.word_wrap)
        self.line_numbers_action.setChecked(self.show_line_numbers)
        self.status_bar_action.setChecked(self.show_status_bar)
        self.app_menu_action.setChecked(self.use_app_menu)
        if self.appimage_dark_mode_action is not None:
            self.appimage_dark_mode_action.setChecked(
                self.effective_appimage_theme() == "dark"
            )
        self.apply_menu_style()
        for mode, action in self.layout_actions.items():
            action.setChecked(mode == self.layout_mode)
        for mode, action in self.drop_behaviour_actions.items():
            action.setChecked(mode == self.drop_open_mode)
        self.set_word_wrap_mode()
        self.text_area.set_line_numbers_visible(self.show_line_numbers)
        self.app_status_bar.setVisible(self.show_status_bar)
        self.apply_layout_mode()
        self.apply_editor_font()

    def effective_appimage_theme(self):
        """Return the explicit launch override or the saved AppImage choice."""
        return self.appimage_theme_override or self.appimage_theme

    def apply_appimage_theme(self, theme, update_actions=True):
        """Apply an AppImage-only theme to the entire Qt application."""
        if not self.appimage_theme_available:
            return

        application = QApplication.instance()
        if application is None:
            return

        if theme == "system":
            application.setStyleSheet("")
            original_style = application.property(
                "nuxpad_original_style"
            )
            restored_style = (
                QStyleFactory.create(str(original_style))
                if original_style
                else None
            )
            if restored_style is not None:
                application.setStyle(restored_style)
        else:
            stylesheet_path = self.appimage_theme_files.get(theme)
            if not stylesheet_path:
                return
            try:
                stylesheet = Path(stylesheet_path).read_text(
                    encoding="utf-8"
                )
            except OSError:
                return

            fusion_style = QStyleFactory.create("Fusion")
            if fusion_style is not None:
                application.setStyle(fusion_style)
            application.setStyleSheet(stylesheet)

        if update_actions:
            for window in tuple(OPEN_WINDOWS):
                action = getattr(
                    window,
                    "appimage_dark_mode_action",
                    None,
                )
                if action is not None:
                    action.blockSignals(True)
                    action.setChecked(theme == "dark")
                    action.blockSignals(False)
                window.refresh_portable_icons()

    def toggle_appimage_dark_mode(self, checked):
        """Switch every open AppImage window between dark and light QSS."""
        if not self.appimage_theme_available:
            return

        selected_theme = "dark" if checked else "light"

        # A direct menu choice takes precedence over a one-launch environment
        # or command-line override.
        os.environ.pop("NUXPAD_APPIMAGE_THEME", None)
        for window in tuple(OPEN_WINDOWS):
            window.appimage_theme = selected_theme
            window.appimage_theme_override = None

        self.apply_appimage_theme(selected_theme)
        self.save_preferences()

    def apply_editor_font(self):
        editor_font = QFont(self.base_font_family, self.base_font_size)
        editor_font.setBold(self.base_font_weight == "bold")
        editor_font.setItalic(self.base_font_slant == "italic")
        self.text_area.setFont(editor_font)

    def open_font_dialog(self):
        current = self.text_area.font()
        selected, accepted = QFontDialog.getFont(current, self, "Font")
        if accepted:
            self.base_font_family = selected.family()
            self.base_font_size = max(6, selected.pointSize())
            self.base_font_weight = "bold" if selected.bold() else "normal"
            self.base_font_slant = "italic" if selected.italic() else "roman"
            self.apply_editor_font()
            self.save_preferences()

    # ---------- Editing ----------
    def text_area_undo(self):
        self.text_area.undo()

    def text_area_redo(self):
        self.text_area.redo()

    def insert_symbol(self, symbol, popup=None):
        """Insert one symbol at the caret and return focus to the editor."""
        cursor = self.text_area.textCursor()
        cursor.insertText(symbol)
        self.text_area.setTextCursor(cursor)
        if popup is not None:
            popup.accept()
        self.text_area.setFocus()
        self.text_area.ensureCursorVisible()

    def open_more_symbols(self, popup=None):
        """Open the operating system's available character-map utility."""
        if popup is not None:
            popup.accept()

        host_environment = host_process_environment()
        host_path = host_environment.get("PATH")

        if sys.platform == "win32":
            system_root = os.environ.get("SystemRoot", r"C:\Windows")
            candidates = (
                (os.path.join(system_root, "System32", "charmap.exe"), []),
                ("charmap.exe", []),
            )
            missing_message = (
                "Windows Character Map could not be found on this system."
            )
        else:
            candidates = (
                ("kcharselect", []),
                ("gucharmap", []),
                ("gnome-characters", []),
                ("charmap", []),
            )
            missing_message = (
                "No supported character-map application was found.\n\n"
                "Install KCharSelect, GNOME Characters, or Gucharmap "
                "to use this option."
            )

        for command, arguments in candidates:
            executable = (
                command
                if os.path.isfile(command)
                else shutil.which(command, path=host_path)
            )
            if executable:
                try:
                    subprocess.Popen(
                        [executable, *arguments],
                        env=host_environment,
                        start_new_session=(sys.platform != "win32"),
                    )
                    self.text_area.setFocus()
                    return
                except OSError:
                    continue

        QMessageBox.information(
            self,
            "More Symbols",
            missing_message,
        )
        self.text_area.setFocus()

    def show_symbols_popup(self):
        """Show a compact curated symbol grid beneath the Symbols button."""
        popup = QDialog(self, Qt.WindowType.Popup)
        popup.setWindowTitle("Symbols")
        popup.setModal(True)

        layout = QGridLayout(popup)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setHorizontalSpacing(5)
        layout.setVerticalSpacing(5)

        symbols = (
            "©", "®", "™", "°", "•", "·", "—", "–",
            "…", "→", "←", "↑", "↓", "✓", "✗", "§",
            "£", "€", "$", "¥", "¢", "±", "×", "÷",
            "≠", "≤", "≥", "≈", "∞", "µ", "¶", "№",
        )

        columns = 8
        for index, symbol in enumerate(symbols):
            button = QToolButton(popup)
            button.setText(symbol)
            button.setToolTip(f"Insert {symbol}")
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setFixedSize(34, 30)
            button.clicked.connect(
                lambda _checked=False, value=symbol: self.insert_symbol(value, popup)
            )
            layout.addWidget(button, index // columns, index % columns)

        separator = QFrame(popup)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(
            separator,
            (len(symbols) + columns - 1) // columns,
            0,
            1,
            columns,
        )

        more_button = QPushButton("More Symbols…", popup)
        more_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        more_button.clicked.connect(
            lambda _checked=False: self.open_more_symbols(popup)
        )
        layout.addWidget(
            more_button,
            (len(symbols) + columns - 1) // columns + 1,
            0,
            1,
            columns,
        )

        popup.adjustSize()
        position = self.symbols_button.mapToGlobal(
            self.symbols_button.rect().bottomLeft()
        )
        popup.move(position)
        popup.exec()

        # Clicking outside the popup closes it; always restore editor focus.
        self.text_area.setFocus()

    def insert_bullet_point(self):
        """Apply a bullet intelligently to the current paragraph."""
        cursor = self.text_area.textCursor()
        block = cursor.block()
        block_text = block.text()
        block_start = block.position()

        cursor.beginEditBlock()

        if not block_text.strip():
            # An empty line becomes a ready-to-type list item.
            cursor.setPosition(block_start)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.insertText("• ")

        elif block_text.startswith("• "):
            # From an existing list item, create the next bullet immediately.
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            cursor.insertText("\n• ")

        else:
            # Turn the current paragraph into a bullet from any caret position.
            original_position = cursor.position()
            cursor.setPosition(block_start)
            cursor.insertText("• ")
            cursor.setPosition(original_position + 2)

        cursor.endEditBlock()
        self.text_area.setTextCursor(cursor)
        self.text_area.setFocus(Qt.FocusReason.OtherFocusReason)
        self.text_area.ensureCursorVisible()

    def formatted_system_date(self):
        """Return the current date using the desktop's locale."""
        return QLocale.system().toString(
            QDateTime.currentDateTime().date(),
            QLocale.FormatType.ShortFormat,
        )

    def formatted_system_time(self):
        """Return the current time using the desktop's locale."""
        return QLocale.system().toString(
            QDateTime.currentDateTime().time(),
            QLocale.FormatType.ShortFormat,
        )

    def formatted_system_timestamp(self):
        """Return the current locale-aware date and time."""
        return QLocale.system().toString(
            QDateTime.currentDateTime(),
            QLocale.FormatType.ShortFormat,
        )

    def insert_text_at_cursor(self, text):
        """Insert text at the caret and return focus to the editor."""
        cursor = self.text_area.textCursor()
        cursor.insertText(text)
        self.text_area.setTextCursor(cursor)
        self.text_area.setFocus()
        self.text_area.ensureCursorVisible()

    def insert_time_date(self):
        """Insert the current system-local date and time at the caret (F5)."""
        self.insert_text_at_cursor(self.formatted_system_timestamp())

    def insert_date(self):
        """Insert the current system-local date at the caret (Ctrl+D)."""
        self.insert_text_at_cursor(self.formatted_system_date())

    def insert_time(self):
        """Insert the current system-local time at the caret (Ctrl+T)."""
        self.insert_text_at_cursor(self.formatted_system_time())

    @staticmethod
    def is_log_document(content):
        """Match classic Notepad behaviour: the first line must be exactly .LOG."""
        first_line = content.splitlines()[0] if content.splitlines() else content
        return first_line == ".LOG"

    def append_log_timestamp(self):
        """Append a timestamp to an opened .LOG document and leave it ready to type."""
        cursor = self.text_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        current_text = self.text_area.toPlainText()
        if current_text and not current_text.endswith("\n"):
            cursor.insertText("\n")
        if current_text and not current_text.endswith("\n\n"):
            cursor.insertText("\n")

        cursor.insertText(self.formatted_system_timestamp() + "\n")
        self.text_area.setTextCursor(cursor)
        self.text_area.ensureCursorVisible()
        self.text_area.setFocus()

    def go_to_line(self):
        """Move the caret to a requested 1-based document line."""
        maximum = max(1, self.text_area.document().blockCount())
        current = self.text_area.textCursor().blockNumber() + 1
        line_number, accepted = QInputDialog.getInt(
            self,
            "Go To Line",
            f"Line number (1–{maximum}):",
            value=current,
            min=1,
            max=maximum,
        )
        if not accepted:
            return

        block = self.text_area.document().findBlockByNumber(line_number - 1)
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        self.text_area.setTextCursor(cursor)
        self.text_area.centerCursor()
        self.text_area.setFocus()

    def show_replace_dialog(self):
        """Show one reusable, modeless Replace dialog."""
        if self.replace_dialog is not None:
            self.replace_dialog.show()
            self.replace_dialog.raise_()
            self.replace_find_entry.setFocus()
            self.replace_find_entry.selectAll()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Replace")
        dialog.setModal(False)
        dialog.setMinimumWidth(420)

        outer = QVBoxLayout(dialog)
        form = QFormLayout()
        self.replace_find_entry = QLineEdit(dialog)
        self.replace_with_entry = QLineEdit(dialog)
        form.addRow("Find:", self.replace_find_entry)
        form.addRow("Replace with:", self.replace_with_entry)
        outer.addLayout(form)

        self.replace_case_checkbox = QCheckBox("Match case", dialog)
        outer.addWidget(self.replace_case_checkbox)

        buttons = QHBoxLayout()
        replace_button = QPushButton("Replace", dialog)
        replace_all_button = QPushButton("Replace All", dialog)
        close_button = QPushButton("Close", dialog)
        buttons.addStretch(1)
        buttons.addWidget(replace_button)
        buttons.addWidget(replace_all_button)
        buttons.addWidget(close_button)
        outer.addLayout(buttons)

        replace_button.clicked.connect(self.replace_next)
        replace_all_button.clicked.connect(self.replace_all)
        close_button.clicked.connect(dialog.close)
        self.replace_find_entry.returnPressed.connect(self.replace_next)
        dialog.finished.connect(self._replace_dialog_closed)

        selected = self.text_area.textCursor().selectedText()
        if selected and "\u2029" not in selected:
            self.replace_find_entry.setText(selected)

        self.replace_dialog = dialog
        dialog.show()
        self.replace_find_entry.setFocus()
        self.replace_find_entry.selectAll()

    def _replace_dialog_closed(self, _result):
        if self.replace_dialog is not None:
            self.replace_dialog.deleteLater()
        self.replace_dialog = None

    def _replace_flags(self):
        flags = QTextDocument.FindFlag(0)
        if self.replace_case_checkbox.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        return flags

    def _selection_matches_replace_query(self, cursor, query):
        if not cursor.hasSelection():
            return False
        selected = cursor.selectedText()
        if self.replace_case_checkbox.isChecked():
            return selected == query
        return selected.casefold() == query.casefold()

    def _find_replace_match(self, query, start_cursor=None):
        document = self.text_area.document()
        flags = self._replace_flags()
        start = QTextCursor(start_cursor or self.text_area.textCursor())
        if start.hasSelection():
            start.setPosition(start.selectionEnd())
        match = document.find(query, start, flags)
        if match.isNull():
            match = document.find(query, QTextCursor(document), flags)
        return match

    def replace_next(self):
        """Replace the selected matching occurrence, or select the next one."""
        query = self.replace_find_entry.text()
        if not query:
            self.replace_find_entry.setFocus()
            return

        cursor = self.text_area.textCursor()
        if self._selection_matches_replace_query(cursor, query):
            cursor.insertText(self.replace_with_entry.text())
            self.text_area.setTextCursor(cursor)

        match = self._find_replace_match(query, self.text_area.textCursor())
        if match.isNull():
            QMessageBox.information(self, "Replace", "No matches found.")
            return

        self.text_area.setTextCursor(match)
        self.text_area.ensureCursorVisible()
        self.text_area.setFocus()

    def replace_all(self):
        """Replace all matches as one undoable edit operation."""
        query = self.replace_find_entry.text()
        if not query:
            self.replace_find_entry.setFocus()
            return

        replacement = self.replace_with_entry.text()
        document = self.text_area.document()
        flags = self._replace_flags()
        scan = QTextCursor(document)
        edit_cursor = QTextCursor(document)
        count = 0

        edit_cursor.beginEditBlock()
        try:
            while True:
                match = document.find(query, scan, flags)
                if match.isNull():
                    break
                match.insertText(replacement)
                scan = QTextCursor(match)
                count += 1
        finally:
            edit_cursor.endEditBlock()

        self.clear_search_results()
        if count == 0:
            QMessageBox.information(self, "Replace", "No matches found.")
        else:
            QMessageBox.information(self, "Replace", f"Replaced {count} occurrence{'s' if count != 1 else ''}.")
        self.replace_find_entry.setFocus(Qt.FocusReason.OtherFocusReason)
        self.replace_find_entry.selectAll()

    def focus_search(self):
        target = self.bottom_search_entry if self.layout_mode in (3, 4) else self.search_entry
        target.setFocus()
        target.selectAll()

    def active_search_text(self):
        return self.bottom_search_entry.text() if self.layout_mode in (3, 4) else self.search_entry.text()

    def on_search_text_changed(self, text):
        """Synchronize both search boxes and invalidate previous results."""
        sender = self.sender()
        other = self.bottom_search_entry if sender is self.search_entry else self.search_entry
        if other.text() != text:
            other.blockSignals(True)
            other.setText(text)
            other.blockSignals(False)
        self.clear_search_results()

    def on_document_text_changed(self):
        self.update_status_counts()
        self.clear_search_results()

    def update_search_counter(self):
        total = len(self.search_matches)
        current = (
            self.current_search_index + 1
            if 0 <= self.current_search_index < total
            else 0
        )
        total_text = (
            f"{total:,}+"
            if self.search_results_truncated
            else f"{total:,}"
        )
        value = f"{current:,}/{total_text}"
        tooltip = (
            f"Showing the first {MAX_SEARCH_MATCHES:,} matches."
            if self.search_results_truncated
            else ""
        )
        self.search_count_label.setText(value)
        self.bottom_search_count_label.setText(value)
        self.search_count_label.setToolTip(tooltip)
        self.bottom_search_count_label.setToolTip(tooltip)
        enabled = total > 0
        self.search_previous_button.setEnabled(enabled)
        self.search_next_button.setEnabled(enabled)
        self.bottom_previous_button.setEnabled(enabled)
        self.bottom_next_button.setEnabled(enabled)

    def clear_search_results(self):
        """Remove search state without changing the editor cursor or scrollbars."""
        self.search_matches.clear()
        self.search_results_truncated = False
        self.current_search_index = -1
        if hasattr(self, "text_area"):
            self.text_area.setExtraSelections([])
        if hasattr(self, "search_count_label"):
            self.update_search_counter()

    def find_text_and_refocus(self, _checked=False):
        """Run Find and return focus to the active search field."""
        self.find_text()
        target = self.bottom_search_entry if self.layout_mode in (3, 4) else self.search_entry
        target.setFocus(Qt.FocusReason.OtherFocusReason)

    def find_text(self, show_message=True):
        """Highlight every literal match without moving the editor cursor."""
        query = self.active_search_text()
        self.search_matches = []
        self.search_results_truncated = False
        self.current_search_index = -1
        self.text_area.setExtraSelections([])
        if not query:
            self.update_search_counter()
            self.focus_search()
            return False

        expression = QRegularExpression(
            QRegularExpression.escape(query),
            QRegularExpression.PatternOption.CaseInsensitiveOption,
        )
        document = self.text_area.document()
        cursor = QTextCursor(document)
        selections = []

        palette = self.text_area.palette()
        highlight = QColor(palette.color(palette.ColorRole.Highlight))
        highlighted_text = palette.color(palette.ColorRole.HighlightedText)

        while len(self.search_matches) < MAX_SEARCH_MATCHES:
            cursor = document.find(expression, cursor)
            if cursor.isNull():
                break
            match_cursor = QTextCursor(cursor)
            self.search_matches.append(match_cursor)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = QTextCursor(match_cursor)
            selection.format = QTextCharFormat()
            selection.format.setBackground(highlight)
            selection.format.setForeground(highlighted_text)
            selections.append(selection)

        if len(self.search_matches) == MAX_SEARCH_MATCHES:
            next_match = document.find(expression, cursor)
            self.search_results_truncated = not next_match.isNull()

        self.text_area.setExtraSelections(selections)
        self.update_search_counter()
        if not self.search_matches and show_message:
            QMessageBox.information(self, "Find", "No matches found.")
        return bool(self.search_matches)

    def _ensure_search_matches(self):
        query = self.active_search_text()
        if not query:
            self.focus_search()
            return False
        if not self.search_matches:
            return self.find_text(show_message=True)
        return True

    def _show_search_match(self, index):
        if not self.search_matches:
            return
        self.current_search_index = index % len(self.search_matches)
        cursor = QTextCursor(self.search_matches[self.current_search_index])
        self.text_area.setTextCursor(cursor)
        self.text_area.ensureCursorVisible()
        self.text_area.setFocus()
        self.update_search_counter()

    def find_next(self):
        """Move to the next match, wrapping to the first."""
        if not self._ensure_search_matches():
            return
        self._show_search_match(self.current_search_index + 1)

    def find_previous(self):
        """Move to the previous match, wrapping to the last."""
        if not self._ensure_search_matches():
            return
        if self.current_search_index < 0:
            self._show_search_match(len(self.search_matches) - 1)
        else:
            self._show_search_match(self.current_search_index - 1)

    # ---------- Toggles / theme ----------
    def set_word_wrap_mode(self):
        mode = (
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if self.word_wrap
            else QPlainTextEdit.LineWrapMode.NoWrap
        )
        self.text_area.setLineWrapMode(mode)

    def toggle_word_wrap(self, checked):
        self.word_wrap = bool(checked)
        self.set_word_wrap_mode()
        self.save_preferences()

    def toggle_line_numbers(self, checked):
        self.show_line_numbers = bool(checked)
        self.text_area.set_line_numbers_visible(self.show_line_numbers)
        self.save_preferences()

    def toggle_status_bar(self, checked):
        self.show_status_bar = bool(checked)
        self.app_status_bar.setVisible(self.show_status_bar)
        if self.show_status_bar:
            self.update_status_counts()
        self.save_preferences()

    def toggle_menu_style(self, checked):
        self.use_app_menu = bool(checked)
        self.apply_menu_style()
        self.save_preferences()

    def apply_menu_style(self):
        """Switch between the native/global menu and toolbar menu buttons."""
        active_popup = QApplication.activePopupWidget()
        if isinstance(active_popup, QMenu):
            active_popup.close()
        self.app_menu_bar.setVisible(self.use_app_menu)
        self.menu_buttons_container.setVisible(not self.use_app_menu)
        self.app_menu_action.blockSignals(True)
        self.app_menu_action.setChecked(self.use_app_menu)
        self.app_menu_action.blockSignals(False)

    def set_drop_open_mode(self, mode):
        """Set whether dropped files replace the active document or open separately."""
        if mode not in ("active_window", "new_window"):
            return
        self.drop_open_mode = mode
        for value, action in self.drop_behaviour_actions.items():
            action.blockSignals(True)
            action.setChecked(value == mode)
            action.blockSignals(False)
        self.save_preferences()

    def set_layout_mode(self, mode):
        if mode not in (1, 2, 3, 4):
            return
        self.layout_mode = mode
        for value, action in self.layout_actions.items():
            action.blockSignals(True)
            action.setChecked(value == mode)
            action.blockSignals(False)
        self.apply_layout_mode()
        self.save_preferences()

    def apply_layout_mode(self):
        """Reorder existing widgets without destroying or recreating them."""
        query = self.search_entry.text() or self.bottom_search_entry.text()
        self.search_entry.blockSignals(True)
        self.bottom_search_entry.blockSignals(True)
        self.search_entry.setText(query)
        self.bottom_search_entry.setText(query)
        self.search_entry.blockSignals(False)
        self.bottom_search_entry.blockSignals(False)

        for widget in (self.toolbar, self.text_area, self.bottom_search):
            self.main_layout.removeWidget(widget)

        split = self.layout_mode in (3, 4)
        self.search_container.setVisible(not split)
        self.bottom_search.setVisible(split)

        if self.layout_mode == 1:
            self.main_layout.addWidget(self.toolbar)
            self.main_layout.addWidget(self.text_area, 1)
        elif self.layout_mode == 2:
            self.main_layout.addWidget(self.text_area, 1)
            self.main_layout.addWidget(self.toolbar)
        elif self.layout_mode == 3:
            self.main_layout.addWidget(self.toolbar)
            self.main_layout.addWidget(self.text_area, 1)
            self.main_layout.addWidget(self.bottom_search)
        else:
            self.main_layout.addWidget(self.bottom_search)
            self.main_layout.addWidget(self.text_area, 1)
            self.main_layout.addWidget(self.toolbar)

    def apply_native_style(self):
        """Use Qt's active operating-system theme without overriding its palette.

        The sole rule below suppresses the automatic menu triangle on the three
        text menu buttons. Colours, fonts, controls, menus, scrollbars, focus
        states, light/dark mode and icon appearance all remain system-managed.
        """
        self.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0px; }")

    # ---------- Printing / Help ----------
    def show_page_setup_dialog(self):
        """Configure compact left, centre and right header/footer fields."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Page Setup")
        dialog.setModal(True)
        dialog.setMinimumWidth(590)

        outer = QVBoxLayout(dialog)
        outer.setContentsMargins(20, 18, 20, 16)
        outer.setSpacing(14)

        explanation = QLabel(
            "Headers and footers are added only when printing.<br>"
            "<b>Placeholders:</b> &amp;F filename, &amp;P page, &amp;N total pages, "
            "&amp;D date, &amp;T time, &amp;A application, &amp;C Confidential.",
            dialog,
        )
        explanation.setWordWrap(True)
        outer.addWidget(explanation)

        def build_section(title, enabled, left_value, center_value, right_value):
            group = QGroupBox(dialog)
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(12, 10, 12, 12)
            group_layout.setSpacing(7)

            enabled_check = QCheckBox(f"Enable {title.lower()}", group)
            enabled_check.setChecked(enabled)
            group_layout.addWidget(enabled_check)

            labels_row = QHBoxLayout()
            labels_row.setSpacing(8)
            for label_text in ("Left", "Centre", "Right"):
                label = QLabel(label_text, group)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                labels_row.addWidget(label, 1)
            group_layout.addLayout(labels_row)

            fields_row = QHBoxLayout()
            fields_row.setSpacing(8)
            left_edit = QLineEdit(left_value, group)
            center_edit = QLineEdit(center_value, group)
            right_edit = QLineEdit(right_value, group)
            fields_row.addWidget(left_edit, 1)
            fields_row.addWidget(center_edit, 1)
            fields_row.addWidget(right_edit, 1)
            group_layout.addLayout(fields_row)

            def update_enabled():
                active = enabled_check.isChecked()
                left_edit.setEnabled(active)
                center_edit.setEnabled(active)
                right_edit.setEnabled(active)

            enabled_check.toggled.connect(update_enabled)
            update_enabled()

            return group, enabled_check, left_edit, center_edit, right_edit

        (
            header_group,
            self.page_setup_header_check,
            self.page_setup_header_left,
            self.page_setup_header_center,
            self.page_setup_header_right,
        ) = build_section(
            "Header",
            self.print_header_enabled,
            self.print_header_left,
            self.print_header_center,
            self.print_header_right,
        )
        outer.addWidget(header_group)

        (
            footer_group,
            self.page_setup_footer_check,
            self.page_setup_footer_left,
            self.page_setup_footer_center,
            self.page_setup_footer_right,
        ) = build_section(
            "Footer",
            self.print_footer_enabled,
            self.print_footer_left,
            self.print_footer_center,
            self.print_footer_right,
        )
        outer.addWidget(footer_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        outer.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.print_header_enabled = self.page_setup_header_check.isChecked()
        self.print_header_left = self.page_setup_header_left.text()
        self.print_header_center = self.page_setup_header_center.text()
        self.print_header_right = self.page_setup_header_right.text()
        self.print_footer_enabled = self.page_setup_footer_check.isChecked()
        self.print_footer_left = self.page_setup_footer_left.text()
        self.print_footer_center = self.page_setup_footer_center.text()
        self.print_footer_right = self.page_setup_footer_right.text()
        self.save_preferences()

    def _expand_print_template(self, template, page_number, page_count):
        """Expand the small set of Nuxpad print placeholders."""
        now = QDateTime.currentDateTime()
        system_locale = QLocale.system()
        filename = os.path.basename(self.file_path) if self.file_path else "Untitled"
        replacements = {
            "&F": filename,
            "&P": str(page_number),
            "&N": str(page_count),
            "&D": system_locale.toString(now.date(), QLocale.FormatType.ShortFormat),
            "&T": system_locale.toString(now.time(), QLocale.FormatType.ShortFormat),
            "&A": APP_NAME,
            "&C": "Confidential",
        }
        result = template
        for token, value in replacements.items():
            result = result.replace(token, value)
        return result

    def _draw_print_line(
        self, painter, rect, left_text, center_text, right_text, page_number, page_count
    ):
        """Draw three independently aligned fields within one header/footer line."""
        third = rect.width() / 3.0
        fields = (
            (
                QRectF(rect.left(), rect.top(), third, rect.height()),
                left_text,
                Qt.AlignmentFlag.AlignLeft,
            ),
            (
                QRectF(rect.left() + third, rect.top(), third, rect.height()),
                center_text,
                Qt.AlignmentFlag.AlignCenter,
            ),
            (
                QRectF(rect.left() + third * 2, rect.top(), third, rect.height()),
                right_text,
                Qt.AlignmentFlag.AlignRight,
            ),
        )

        for field_rect, template, horizontal_alignment in fields:
            if not template:
                continue
            text = self._expand_print_template(template, page_number, page_count)
            painter.drawText(
                field_rect,
                int(horizontal_alignment | Qt.AlignmentFlag.AlignVCenter),
                text,
            )

    def _print_document_with_header_footer(self, printer):
        """Paginate plain text with reliable PDF/printer coordinates."""
        painter = QPainter()
        if not painter.begin(printer):
            QMessageBox.critical(
                self,
                "Print Error",
                "Nuxpad could not start the print or PDF output job.",
            )
            return False

        completed = False
        try:
            # Use the printer's actual paintable rectangle at its selected
            # resolution. QTextDocument must use the same paint device or its
            # pagination can disagree with the PDF/printer paint engine.
            page_rect = QRectF(
                printer.pageLayout().paintRectPixels(printer.resolution())
            )
            if page_rect.width() <= 0 or page_rect.height() <= 0:
                raise RuntimeError("The selected printer returned an invalid page size.")

            dpi_x = max(72, printer.logicalDpiX())
            dpi_y = max(72, printer.logicalDpiY())
            side_margin = dpi_x * 0.25
            vertical_gap = dpi_y * 0.12
            body_padding = dpi_y * 0.10

            painter.setFont(QApplication.font())
            metrics = painter.fontMetrics()
            line_height = max(metrics.height(), int(dpi_y * 0.14))

            # Reserve a full two-line band for each enabled header/footer,
            # plus an additional inner gap between metadata and document text.
            header_space = (
                line_height * 2 + vertical_gap + body_padding
                if self.print_header_enabled
                else body_padding
            )
            footer_space = (
                line_height * 2 + vertical_gap + body_padding
                if self.print_footer_enabled
                else body_padding
            )

            content_width = page_rect.width() - side_margin * 2
            content_height = page_rect.height() - header_space - footer_space
            if content_width <= 1 or content_height <= 1:
                raise RuntimeError(
                    "The printable page area is too small for the selected settings."
                )

            content_rect = QRectF(
                page_rect.left() + side_margin,
                page_rect.top() + header_space,
                content_width,
                content_height,
            )

            document = QTextDocument(self)
            document.documentLayout().setPaintDevice(printer)
            document.setDefaultFont(self.text_area.font())
            document.setDocumentMargin(0)
            document.setPlainText(self.text_area.toPlainText())

            # The editor may use a dark desktop palette with pale foreground
            # text. A PDF page is white, so inheriting that colour makes the
            # printed document almost invisible. Apply black only to this
            # temporary print document; the editor and file remain unchanged.
            print_cursor = QTextCursor(document)
            print_cursor.select(QTextCursor.SelectionType.Document)
            print_format = QTextCharFormat()
            print_format.setForeground(QColor(Qt.GlobalColor.black))
            print_cursor.mergeCharFormat(print_format)

            document.setPageSize(QSizeF(content_width, content_height))

            page_count = max(1, int(document.pageCount()))

            for page_index in range(page_count):
                if page_index and not printer.newPage():
                    raise RuntimeError(
                        "The print engine stopped before all pages were produced."
                    )

                page_number = page_index + 1

                # Header and footer use the normal Qt interface font and
                # a print-safe black foreground, independent of desktop theme.
                painter.setFont(QApplication.font())
                painter.setPen(QColor(Qt.GlobalColor.black))

                if self.print_header_enabled:
                    header_rect = QRectF(
                        page_rect.left() + side_margin,
                        page_rect.top() + vertical_gap,
                        content_width,
                        line_height,
                    )
                    self._draw_print_line(
                        painter,
                        header_rect,
                        self.print_header_left,
                        self.print_header_center,
                        self.print_header_right,
                        page_number,
                        page_count,
                    )

                if self.print_footer_enabled:
                    footer_rect = QRectF(
                        page_rect.left() + side_margin,
                        page_rect.bottom() - line_height - vertical_gap,
                        content_width,
                        line_height,
                    )
                    self._draw_print_line(
                        painter,
                        footer_rect,
                        self.print_footer_left,
                        self.print_footer_center,
                        self.print_footer_right,
                        page_number,
                        page_count,
                    )

                # Draw subtle separator rules at the edge of the reserved bands.
                painter.save()
                painter.setPen(QColor(160, 160, 160))
                if self.print_header_enabled:
                    separator_y = content_rect.top() - body_padding / 2
                    painter.drawLine(
                        int(content_rect.left()),
                        int(separator_y),
                        int(content_rect.right()),
                        int(separator_y),
                    )
                if self.print_footer_enabled:
                    separator_y = content_rect.bottom() + body_padding / 2
                    painter.drawLine(
                        int(content_rect.left()),
                        int(separator_y),
                        int(content_rect.right()),
                        int(separator_y),
                    )
                painter.restore()

                # Draw one document page. The clipping rectangle is local to the
                # printable content area; the document is shifted upward for
                # subsequent pages.
                painter.save()
                painter.translate(content_rect.left(), content_rect.top())
                painter.setClipRect(QRectF(0, 0, content_width, content_height))
                painter.translate(0, -page_index * content_height)
                document.drawContents(
                    painter,
                    QRectF(
                        0,
                        page_index * content_height,
                        content_width,
                        content_height,
                    ),
                )
                painter.restore()

            completed = True
            return True

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Print Error",
                f"Nuxpad could not complete the print or PDF output.\n\n{exc}",
            )
            return False
        finally:
            if painter.isActive():
                painter.end()
            if not completed and printer.outputFileName():
                # Avoid leaving behind an apparently valid but incomplete PDF.
                try:
                    output_path = printer.outputFileName()
                    if os.path.isfile(output_path) and os.path.getsize(output_path) == 0:
                        os.remove(output_path)
                except OSError:
                    pass

    def print_document(self):
        """Open the native print dialog and print with headers and footers."""
        # ScreenResolution is Qt's most portable mode for QTextDocument:
        # screen and printer font metrics stay consistent, while PDF output
        # remains vector/searchable.
        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Print")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._print_document_with_header_footer(printer)

    def show_keyboard_shortcuts_dialog(self):
        """Show the current Nuxpad keyboard shortcuts in a compact native dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Keyboard Shortcuts")
        dialog.setModal(True)
        dialog.setMinimumWidth(460)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

        title = QLabel("<h3>Keyboard Shortcuts</h3>", dialog)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        shortcuts = QLabel(
            "<table cellspacing='4' cellpadding='2' width='100%'>"

            "<tr><td colspan='2'><b>File</b></td></tr>"
            "<tr><td>New</td><td align='right'>Ctrl+N</td></tr>"
            "<tr><td>Open</td><td align='right'>Ctrl+O</td></tr>"
            "<tr><td>Save</td><td align='right'>Ctrl+S</td></tr>"
            "<tr><td>Save As</td><td align='right'>Ctrl+Shift+S</td></tr>"
            "<tr><td>Rename</td><td align='right'>Ctrl+Alt+R</td></tr>"
            "<tr><td>Print</td><td align='right'>Ctrl+P</td></tr>"

            "<tr><td colspan='2'><br><b>Edit</b></td></tr>"
            "<tr><td>Undo</td><td align='right'>Ctrl+Z</td></tr>"
            "<tr><td>Redo</td><td align='right'>Ctrl+Y</td></tr>"
            "<tr><td>Cut</td><td align='right'>Ctrl+X</td></tr>"
            "<tr><td>Copy</td><td align='right'>Ctrl+C</td></tr>"
            "<tr><td>Paste</td><td align='right'>Ctrl+V</td></tr>"
            "<tr><td>Select All</td><td align='right'>Ctrl+A</td></tr>"

            "<tr><td colspan='2'><br><b>Insert</b></td></tr>"
            "<tr><td>List</td><td align='right'>Ctrl+L</td></tr>"
            "<tr><td>Date</td><td align='right'>Ctrl+D</td></tr>"
            "<tr><td>Time</td><td align='right'>Ctrl+T</td></tr>"
            "<tr><td>Date + Time</td><td align='right'>F5</td></tr>"

            "<tr><td colspan='2'><br><b>Search</b></td></tr>"
            "<tr><td>Find</td><td align='right'>Ctrl+F</td></tr>"
            "<tr><td>Go To Line</td><td align='right'>Ctrl+G</td></tr>"
            "<tr><td>Replace</td><td align='right'>Ctrl+H</td></tr>"

            "<tr><td colspan='2'><br><b>Application</b></td></tr>"
            "<tr><td>New Window</td><td align='right'>Ctrl+Shift+N</td></tr>"
            "<tr><td>Exit</td><td align='right'>Ctrl+Q</td></tr>"

            "</table>",
            dialog,
        )
        shortcuts.setTextFormat(Qt.TextFormat.RichText)
        shortcuts.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(shortcuts)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, parent=dialog)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.exec()

    def show_about_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("About")
        dialog.setModal(True)
        dialog.setMinimumWidth(390)

        window_icon_path = resource_path("icons", "nuxpad.png")
        if os.path.isfile(window_icon_path):
            dialog.setWindowIcon(QIcon(window_icon_path))

        icon_path = resource_path("icons", "nuxpad-about.png")
        if not os.path.isfile(icon_path):
            icon_path = window_icon_path

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(10)

        logo_label = QLabel(dialog)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            logo_label.setPixmap(
                pixmap.scaled(
                    112,
                    112,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            layout.addWidget(logo_label)

        title = QLabel(f"<h2>{APP_NAME}</h2>", dialog)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version = QLabel(f"Version {APP_VERSION}", dialog)
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        tagline = QLabel("<b>Simple. Fast. Focused.</b>", dialog)
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tagline)

        description = QLabel(
            "A lightweight text editor for Linux and Windows, inspired by the simplicity "
            "of Notepad and the practicality of WordPad.",
            dialog,
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)

        details = QLabel(
            '<a href="https://github.com/brunonlinespace/nuxpad.py">'
            "github.com/brunonlinespace/nuxpad.py</a><br>"
            "Built with Python and Qt.<br><br>"
            "Copyright © 2026 Bruno Machado<br>"
            '[<a href="https://github.com/brunonlinespace">'
            "github.com/brunonlinespace</a>]<br>"
            "Licensed under the GNU General Public License v3 or later.",
            dialog,
        )
        details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        details.setOpenExternalLinks(True)
        details.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(details)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, parent=dialog)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.exec()

    # ---------- Files ----------
    def update_title(self):
        """Show the current filename and app name; keep version details in About."""
        prefix = "*" if not self.content_saved else ""
        name = os.path.basename(self.file_path) if self.file_path else "Untitled"
        self.setWindowTitle(f"{prefix}{name} — {APP_NAME}")

    def on_modification_changed(self, modified):
        if self._loading:
            return
        self.content_saved = not modified
        self.update_title()

    def update_status_counts(self):
        """Update the status-bar path and counters efficiently."""
        if not hasattr(self, "text_area"):
            return

        display_path = self.file_path if self.file_path else "Untitled"
        if hasattr(self, "path_label"):
            self.path_label.setText(display_path)
            self.path_label.setToolTip(display_path)

        if not self.show_status_bar:
            return

        document = self.text_area.document()
        lines = max(1, document.blockCount())
        chars = max(0, document.characterCount() - 1)
        self.lines_label.setText(f"Lines: {lines:,}")
        self.chars_label.setText(f"Chars: {chars:,}")

    @staticmethod
    def _content_signature(data):
        """Return a stable signature for the exact encoded file bytes."""
        return (
            len(data),
            hashlib.sha256(data).digest(),
        )

    @classmethod
    def _disk_signature(cls, file_path):
        """Hash a file so same-size or timestamp-preserved edits are found."""
        if not file_path:
            return None

        digest = hashlib.sha256()
        size = 0
        try:
            with open(file_path, "rb") as handle:
                while True:
                    chunk = handle.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    digest.update(chunk)
        except OSError:
            return None

        return (
            size,
            digest.digest(),
        )

    def _external_change_action(self):
        """Ask what to do when the open file changed after it was loaded."""
        if not self.file_path or self.file_disk_signature is None:
            return "overwrite"

        current_signature = self._disk_signature(self.file_path)
        if current_signature == self.file_disk_signature:
            return "overwrite"

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("File Changed on Disk")
        dialog.setText(
            "This file has changed on disk since Nuxpad opened or saved it."
        )
        dialog.setInformativeText(
            "Choose Reload to discard the edits currently in Nuxpad and use "
            "the disk copy, Save As to keep both versions, or Overwrite to "
            "replace the disk copy with the text currently in Nuxpad."
        )

        reload_button = dialog.addButton(
            "Reload",
            QMessageBox.ButtonRole.ActionRole,
        )
        reload_button.setEnabled(current_signature is not None)
        save_as_button = dialog.addButton(
            "Save As…",
            QMessageBox.ButtonRole.ActionRole,
        )
        overwrite_button = dialog.addButton(
            "Overwrite",
            QMessageBox.ButtonRole.DestructiveRole,
        )
        cancel_button = dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.setDefaultButton(cancel_button)
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked is reload_button:
            return "reload"
        if clicked is save_as_button:
            return "save_as"
        if clicked is overwrite_button:
            return "overwrite"
        return "cancel"

    def check_save_changes(self):
        if self.content_saved:
            return True
        answer = QMessageBox.question(
            self,
            APP_NAME,
            "Do you want to save changes?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save_file()
        if answer == QMessageBox.StandardButton.Discard:
            return True
        return False

    def new_file(self):
        if not self.check_save_changes():
            return
        self._loading = True
        self.clear_search_results()
        self.text_area.clear()
        self.text_area.document().setModified(False)
        self._loading = False
        self.file_path = None
        self.file_encoding = "utf-8"
        self.file_bom = b""
        self.file_newline = "\n"
        self.file_disk_signature = None
        self.content_saved = True
        self.update_title()
        self.update_status_counts()
        self.text_area.setFocus()

    def new_window(self, file_path=None):
        """Open an independently managed editor window in this Qt process."""
        if isinstance(file_path, bool):
            file_path = None
        window = Nuxpad(file_path)
        window.show()
        return window

    def open_file(self):
        if not self.check_save_changes():
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Text Documents (*.txt);;All Files (*)")
        if file_path:
            self.load_file(file_path, check_changes=False)

    @staticmethod
    def inspect_text_file(file_path):
        """Return ``(is_safe, reason)`` after basic path and size checks.

        Encoding is deliberately handled later by :meth:`load_file`, because a
        valid text document may be UTF-8, BOM-marked Unicode, or a legacy
        single-byte encoding selected by the user.
        """
        try:
            if not os.path.isfile(file_path):
                return False, "The selected path is not a regular file."
            size = os.path.getsize(file_path)
            if size > MAX_FILE_SIZE:
                return False, (
                    f"The file is larger than Nuxpad's {MAX_FILE_SIZE // (1024 * 1024)} MiB "
                    "safety limit."
                )
        except OSError as exc:
            return False, f"Could not inspect the file:\n{exc}"
        return True, ""

    @staticmethod
    def _decode_bom_text(data):
        """Decode BOM-marked Unicode and return ``(text, encoding, bom)``.

        The longest BOMs are checked first because UTF-32 LE begins with the
        same two bytes as UTF-16 LE.
        """
        bom_map = (
            (codecs.BOM_UTF32_LE, "utf-32-le"),
            (codecs.BOM_UTF32_BE, "utf-32-be"),
            (codecs.BOM_UTF8, "utf-8"),
            (codecs.BOM_UTF16_LE, "utf-16-le"),
            (codecs.BOM_UTF16_BE, "utf-16-be"),
        )
        for bom, encoding in bom_map:
            if data.startswith(bom):
                return data[len(bom):].decode(encoding, errors="strict"), encoding, bom
        return None

    @staticmethod
    def _looks_binary_text(text):
        """Conservatively reject decoded content dominated by control bytes."""
        if "\x00" in text:
            return True
        if not text:
            return False
        controls = sum(
            1 for char in text
            if ord(char) < 32 and char not in "\t\n\r\f\b"
        )
        return controls / len(text) > 0.02

    def _choose_fallback_encoding(self, file_path):
        system_encoding = locale.getpreferredencoding(False) or "utf-8"
        choices = [
            "Windows-1252",
            "ISO-8859-1",
            "UTF-16 LE",
            "UTF-16 BE",
            f"System encoding ({system_encoding})",
        ]
        selected, accepted = QInputDialog.getItem(
            self,
            "Choose Text Encoding",
            (
                f"{os.path.basename(file_path)} is not valid UTF-8.\n\n"
                "Open using:"
            ),
            choices,
            0,
            False,
        )
        if not accepted:
            return None
        return {
            "Windows-1252": "cp1252",
            "ISO-8859-1": "iso-8859-1",
            "UTF-16 LE": "utf-16-le",
            "UTF-16 BE": "utf-16-be",
            f"System encoding ({system_encoding})": system_encoding,
        }[selected]

    @staticmethod
    def _detect_newline_style(content):
        """Return the predominant line-ending style in decoded text."""
        crlf = content.count("\r\n")
        lf = content.count("\n") - crlf
        cr = content.count("\r") - crlf
        counts = (
            (crlf, "\r\n"),
            (lf, "\n"),
            (cr, "\r"),
        )
        count, newline = max(counts, key=lambda item: item[0])
        return newline if count else "\n"

    @staticmethod
    def _normalise_newlines(content):
        """Convert decoded line endings to Qt's internal LF representation."""
        return content.replace("\r\n", "\n").replace("\r", "\n")

    def load_file(self, file_path, check_changes=True, show_error=True):
        if check_changes and not self.check_save_changes():
            return False

        is_safe, reason = self.inspect_text_file(file_path)
        if not is_safe:
            if show_error:
                QMessageBox.warning(
                    self,
                    "Unsupported File",
                    f"Nuxpad did not open:\n{os.path.basename(file_path)}\n\n{reason}",
                )
            return False

        encoding = "unknown encoding"
        bom = b""
        try:
            with open(file_path, "rb") as handle:
                data = handle.read()

            decoded = self._decode_bom_text(data)
            if decoded is not None:
                content, encoding, bom = decoded
            else:
                try:
                    content = data.decode("utf-8", errors="strict")
                    encoding, bom = "utf-8", b""
                except UnicodeDecodeError:
                    encoding = self._choose_fallback_encoding(file_path)
                    if encoding is None:
                        return False
                    content = data.decode(encoding, errors="strict")
                    bom = b""

            if self._looks_binary_text(content):
                if show_error:
                    QMessageBox.warning(
                        self,
                        "Unsupported File",
                        "The file appears to contain binary data rather than plain text.",
                    )
                return False

            newline_style = self._detect_newline_style(content)
            content = self._normalise_newlines(content)
        except UnicodeDecodeError as exc:
            if show_error:
                QMessageBox.warning(
                    self,
                    "Encoding Error",
                    f"The file could not be decoded using {encoding}:\n{exc}",
                )
            return False
        except MemoryError:
            if show_error:
                QMessageBox.critical(self, "File Too Large", "The file is too large to open safely.")
            return False
        except OSError as exc:
            if show_error:
                QMessageBox.critical(self, "Error", f"Could not open file:\n{exc}")
            return False
        except Exception as exc:
            if show_error:
                QMessageBox.critical(self, "Error", f"Nuxpad could not open this file safely:\n{exc}")
            return False

        self._loading = True
        try:
            self.clear_search_results()
            self.text_area.setPlainText(content)
            self.text_area.document().setModified(False)
        except MemoryError:
            if show_error:
                QMessageBox.critical(
                    self,
                    "File Too Large",
                    "The decoded document is too large to load into the editor safely.",
                )
            return False
        finally:
            self._loading = False

        self.file_path = os.path.abspath(file_path)
        self.file_encoding = encoding
        self.file_bom = bom
        self.file_newline = newline_style
        self.file_disk_signature = self._content_signature(data)
        self.content_saved = True
        self.update_title()
        self.update_status_counts()
        self.text_area.setFocus()

        # Classic Notepad-style logging: opening a file whose first line is
        # exactly ".LOG" appends a locale-aware timestamp and marks it modified.
        if self.is_log_document(content):
            self.append_log_timestamp()

        return True

    @staticmethod
    def _default_created_file_mode():
        """Return the normal 0666 mode after applying the process umask."""
        current_umask = os.umask(0)
        os.umask(current_umask)
        return 0o666 & ~current_umask

    def save_file(self, check_external_change=True):
        if not self.file_path:
            return self.save_as_file()

        if check_external_change:
            action = self._external_change_action()
            if action == "reload":
                self.load_file(
                    self.file_path,
                    check_changes=False,
                    show_error=True,
                )
                return False
            if action == "save_as":
                return self.save_as_file()
            if action != "overwrite":
                return False

        temporary = None
        descriptor = None
        try:
            content = self.text_area.toPlainText()
            if self.file_newline != "\n":
                content = content.replace("\n", self.file_newline)
            payload = self.file_bom + content.encode(
                self.file_encoding,
                errors="strict",
            )

            # Preserve symbolic links by writing through them. Encoding is
            # completed before opening the target, so encoding failures cannot
            # truncate the linked file.
            if os.path.islink(self.file_path):
                with open(self.file_path, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
            else:
                parent = os.path.dirname(self.file_path) or "."
                basename = os.path.basename(self.file_path)
                try:
                    existing_mode = os.stat(self.file_path).st_mode & 0o7777
                except FileNotFoundError:
                    # The file may have been removed after the pre-save
                    # external-change check. Treat it as a new file rather than
                    # failing because of an exists()/stat() race.
                    existing_mode = self._default_created_file_mode()

                descriptor, temporary = tempfile.mkstemp(
                    prefix=f".{basename}.nuxpad-",
                    suffix=".tmp",
                    dir=parent,
                )
                if hasattr(os, "fchmod"):
                    os.fchmod(descriptor, existing_mode)
                with os.fdopen(descriptor, "wb") as handle:
                    descriptor = None
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self.file_path)
                temporary = None

                # Make the rename durable where the filesystem supports
                # directory fsync. Failure here does not invalidate the save.
                try:
                    directory_fd = os.open(parent, os.O_RDONLY)
                    try:
                        os.fsync(directory_fd)
                    finally:
                        os.close(directory_fd)
                except OSError:
                    pass

            self.file_disk_signature = self._content_signature(payload)
            self.text_area.document().setModified(False)
            self.content_saved = True
            self.update_title()
            self.update_status_counts()
            return True

        except UnicodeEncodeError as exc:
            QMessageBox.critical(
                self,
                "Encoding Error",
                (
                    f"This document contains characters that cannot be saved as "
                    f"{self.file_encoding}.\n\n{exc}\n\n"
                    "No changes were written."
                ),
            )
            return False
        except MemoryError:
            QMessageBox.critical(
                self,
                "Save Error",
                "The document is too large to encode safely. No changes were written.",
            )
            return False
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Could not save file:\n{exc}")
            return False
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if temporary:
                try:
                    os.remove(temporary)
                except OSError:
                    pass

    def rename_current_file(self):
        """Rename the current file on disk while keeping it open in Nuxpad."""
        if not self.file_path:
            QMessageBox.information(
                self,
                "Rename",
                "This document has not been saved yet. Use Save As to give it a name.",
            )
            return False

        old_path = os.path.abspath(self.file_path)
        old_name = os.path.basename(old_path)
        parent_dir = os.path.dirname(old_path)

        new_name, accepted = QInputDialog.getText(
            self,
            "Rename",
            "New filename:",
            QLineEdit.EchoMode.Normal,
            old_name,
        )
        if not accepted:
            return False

        new_name = new_name.strip()
        if not new_name:
            QMessageBox.warning(
                self,
                "Rename",
                "The filename cannot be empty.",
            )
            return False

        # Rename only within the current directory. Path separators would make
        # this a move operation rather than a simple rename.
        if os.path.basename(new_name) != new_name or new_name in (".", ".."):
            QMessageBox.warning(
                self,
                "Rename",
                "Enter a filename only, without a folder path.",
            )
            return False

        new_path = os.path.abspath(os.path.join(parent_dir, new_name))
        if new_path == old_path:
            return True

        # On case-insensitive filesystems, normcase catches names that resolve
        # to the same path while still allowing a case-only rename where valid.
        existing_target = os.path.exists(new_path)
        if existing_target:
            answer = QMessageBox.question(
                self,
                "Replace Existing File?",
                f'A file named "{new_name}" already exists.\n\n'
                "Replace it with the current file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return False

        try:
            if existing_target:
                os.replace(old_path, new_path)
            else:
                os.rename(old_path, new_path)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Rename Failed",
                f"Nuxpad could not rename the file.\n\n{exc}",
            )
            return False

        self.file_path = new_path
        self.update_title()
        self.update_status_counts()
        return True

    def save_as_file(self):
        """Save under a new name, adding .txt when no extension was entered."""
        initial_path = self.file_path or os.path.join(os.path.expanduser("~"), "Untitled.txt")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            initial_path,
            "Text Documents (*.txt);;All Files (*)",
        )
        if not file_path:
            return False

        # Preserve explicit extensions such as .log, .md, .json, or .py.
        # Only an extensionless name receives Nuxpad's default .txt suffix.
        filename = os.path.basename(file_path)
        _stem, extension = os.path.splitext(filename)
        if not extension:
            file_path += ".txt"

        previous_path = self.file_path
        previous_signature = self.file_disk_signature
        self.file_path = os.path.abspath(file_path)
        self.file_disk_signature = None
        if self.save_file(check_external_change=False):
            return True

        # A failed Save As must not silently detach the document from its
        # original file or leave the title/status bar inconsistent.
        self.file_path = previous_path
        self.file_disk_signature = previous_signature
        self.update_title()
        self.update_status_counts()
        return False

    # ---------- Native drag-and-drop ----------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile() and os.path.isfile(url.toLocalFile())]
        if files:
            self.open_dropped_files(files)
            event.acceptProposedAction()

    def open_dropped_files(self, files):
        files = [os.path.abspath(path) for path in files if os.path.isfile(path)]
        if not files:
            return

        accepted = []
        rejected = []
        for path in files:
            is_text, reason = self.inspect_text_file(path)
            if is_text:
                accepted.append(path)
            else:
                rejected.append((path, reason))

        if rejected:
            names = "\n".join(f"• {os.path.basename(path)}" for path, _ in rejected[:10])
            if len(rejected) > 10:
                names += f"\n• …and {len(rejected) - 10} more"
            QMessageBox.warning(
                self,
                "Unsupported Files Skipped",
                "Nuxpad could not safely inspect these files, so they were skipped:\n\n" + names,
            )

        if not accepted:
            return

        if self.drop_open_mode == "new_window":
            # The current document remains untouched, even when it has unsaved changes.
            for path in accepted:
                self.new_window(path)
            return

        # Default behaviour: replace the active document after the normal
        # save/discard/cancel prompt. Extra dropped files open separately.
        if not self.check_save_changes():
            return

        first, *rest = accepted
        if self.load_file(first, check_changes=False):
            for path in rest:
                self.new_window(path)

    def closeEvent(self, event):
        if self.check_save_changes():
            event.accept()
        else:
            event.ignore()


def main():
    configure_platform_identity()

    app = QApplication(sys.argv)
    app.setProperty(
        "nuxpad_original_style",
        app.style().objectName(),
    )
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("brunonlinespace")
    if sys.platform != "win32":
        app.setDesktopFileName("nuxpad")

    icon_path = resource_path("icons", "nuxpad.png")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # QApplication removes Qt-specific options from its argument list. Every
    # remaining regular file is opened, matching the desktop entry's %F field.
    file_arguments = [
        os.path.abspath(argument)
        for argument in app.arguments()[1:]
        if os.path.isfile(argument)
    ]

    window = Nuxpad(file_arguments[0] if file_arguments else None)
    window.show()
    for file_path in file_arguments[1:]:
        window.new_window(file_path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
